"""Phase 192 Dual-Mode Unit Tests (52 tests) — 40th Milestone Auditor (40/40):
Real-Hardware ILME-FX3 (Ver. 7.02) No-UVC USB Gadget Stack, USB-PD (NP-FZ100) vs
DC-C1 (>=65W / 5A) Power-Budget, Dual-Media .cube User LUT Path-Asymmetry &
Cine EI (800 / 12800) Auditor.
"""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

from fx3_firmware_lab import (  # noqa: E402
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CFEXPRESS_A_USER_LUT_DIR_P192,
    EXPECTED_CDC_NCM_KO_BYTES_P192,
    EXPECTED_FX3_APPFW_BYTES_P192,
    EXPECTED_FX3_CPAPP_BYTES_P192,
    EXPECTED_FX3_MPR_BYTES_P192,
    EXPECTED_FX3_RTMP_BYTES_P192,
    EXPECTED_FX3_SRT_BYTES_P192,
    EXPECTED_FX3_USBBP_BYTES_P192,
    EXPECTED_FX3_USBCMN_BYTES_P192,
    EXPECTED_FX3_USBCTL_BYTES_P192,
    EXPECTED_FX3_VERIC_BYTES_P192,
    EXPECTED_FX6_APPFW_BYTES_P192,
    EXPECTED_FX6_USBCMN_BYTES_P192,
    EXPECTED_USBG_STILLIMAGE_KO_BYTES_P192,
    EXPECTED_USBG_STORAGE_KO_BYTES_P192,
    EXPECTED_USB_BUSPWR_KO_BYTES_P192,
    EXPECTED_USB_F_UVC_KO_BYTES_P192,
    PHASE_192_SCHEMA,
    PHASE_192_VERSION,
    SD_USER_LUT_DIR_P192,
    VALID_BRIDGE_CLASSES,
    analyze_realhw_nouvc_dcc1_pd_lut_path_cineei,
    build_clean_room_realhw_nouvc_dcc1_lut_cineei_fixtures,
    build_phase192_compat_matrix,
    evaluate_nouvc_gadget_and_network_streaming,
    evaluate_phase192_write_guard,
    evaluate_power_delivery_matrix,
    evaluate_rmt_p1bt_and_clip_flag_matrix,
    evaluate_user_lut_path_and_cine_ei,
    realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict,
    validate_cube_text_bounded,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402
from fx3_firmware_lab import realhw_nouvc_dcc1_pd_lut_path_cineei_auditor as mod_p192  # noqa: E402


def _make_cube_17_text(bad_voxel: str = "") -> str:
    lines = ["TITLE \"Test17\"", "LUT_3D_SIZE 17"]
    total = 17 ** 3
    for idx in range(total):
        if bad_voxel and idx == 10:
            lines.append(bad_voxel)
        else:
            v = (idx % 17) / 16.0
            lines.append(f"{v:.4f} {v:.4f} {v:.4f}")
    return "\n".join(lines) + "\n"


class TestRealhwNouvcDcc1PdLutPathCineei(unittest.TestCase):
    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        src_path = Path(mod_p192.__file__)
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "open", "builtin open() is forbidden")
            if isinstance(node, ast.Attribute):
                self.assertFalse(
                    node.attr.startswith(("write", "unlink", "rmdir", "mkdir", "chmod", "chown")),
                    f"forbidden mutating attribute: {node.attr}",
                )
        self.assertIn("os.O_RDONLY", src_path.read_text(encoding="utf-8"))

    def test_02_clean_room_report_passes_under_sla(self) -> None:
        t0 = time.monotonic()
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 1.0)
        self.assertEqual(rep.schema_version, PHASE_192_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_192_VERSION)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_03_auto_mode_under_sla_and_cache_hit_on_second_call(self) -> None:
        mod_p192._DONOR_SCAN_CACHE.clear()
        t0 = time.monotonic()
        r1 = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
        dt1 = time.monotonic() - t0
        self.assertLess(dt1, 6.0)
        self.assertTrue(r1.all_checks_passed)
        if r1.mode == "LOCAL_DONOR_VERIFIED":
            self.assertLess(dt1, 0.50)
            self.assertFalse(r1.cache_hit)
            t1 = time.monotonic()
            r2 = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
            dt2 = time.monotonic() - t1
            self.assertTrue(r2.cache_hit)
            self.assertLess(dt2, 0.05)
            self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_04_clean_room_deterministic_sha256(self) -> None:
        r1 = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=True)
        r2 = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=True)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.report_sha256), 64)

    def test_05_missing_donor_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td, mock.patch(
            "fx3_firmware_lab.realhw_nouvc_dcc1_pd_lut_path_cineei_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(
                clean_room=False,
                repo_root=Path(td),
            )
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_checks_passed)

    def test_06_env_force_clean_room_overrides_local_donors(self) -> None:
        prev = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
        os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        try:
            rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)
        finally:
            if prev is None:
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            else:
                os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = prev

    def test_07_hard_safety_flags_always_false_and_zero(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.persistent_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_08_json_serialization_zero_elf_magic_leak(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=True)
        raw = json.dumps(realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict(rep), sort_keys=True)
        self.assertNotIn("ELF", raw)
        self.assertNotIn("\\x7fELF", raw)

    def test_09_local_donor_verified_exact_file_sizes(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
        if rep.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Local donors unavailable in clean-room-only CI environment")
        sz = rep.donor_file_sizes
        self.assertEqual(sz["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P192)
        self.assertEqual(sz["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P192)
        self.assertEqual(sz["fx3_usbcmn"], EXPECTED_FX3_USBCMN_BYTES_P192)
        self.assertEqual(sz["fx6_usbcmn"], EXPECTED_FX6_USBCMN_BYTES_P192)
        self.assertEqual(sz["fx3_usbctl"], EXPECTED_FX3_USBCTL_BYTES_P192)
        self.assertEqual(sz["fx3_usbbp"], EXPECTED_FX3_USBBP_BYTES_P192)
        self.assertEqual(sz["fx3_veric"], EXPECTED_FX3_VERIC_BYTES_P192)
        self.assertEqual(sz["fx3_rtmp"], EXPECTED_FX3_RTMP_BYTES_P192)
        self.assertEqual(sz["fx3_srt"], EXPECTED_FX3_SRT_BYTES_P192)
        self.assertEqual(sz["fx3_mpr"], EXPECTED_FX3_MPR_BYTES_P192)
        self.assertEqual(sz["fx3_cpapp"], EXPECTED_FX3_CPAPP_BYTES_P192)
        self.assertEqual(sz["kmod_usb_buspwr"], EXPECTED_USB_BUSPWR_KO_BYTES_P192)
        self.assertEqual(sz["kmod_cdc_ncm"], EXPECTED_CDC_NCM_KO_BYTES_P192)
        self.assertEqual(sz["kmod_usbg_storage"], EXPECTED_USBG_STORAGE_KO_BYTES_P192)
        self.assertEqual(sz["kmod_usbg_stillimage"], EXPECTED_USBG_STILLIMAGE_KO_BYTES_P192)
        self.assertEqual(sz["kmod_usb_f_uvc"], EXPECTED_USB_F_UVC_KO_BYTES_P192)

    def test_10_clean_room_fixtures_complete(self) -> None:
        fx = build_clean_room_realhw_nouvc_dcc1_lut_cineei_fixtures()
        expected_keys = {
            "fx3_appfw",
            "fx6_appfw",
            "fx3_usbcmn",
            "fx6_usbcmn",
            "fx3_usbctl",
            "fx3_usbbp",
            "fx3_veric",
            "fx3_rtmp",
            "fx3_srt",
            "fx3_mpr",
            "fx3_cpapp",
            "kmod_cdc_ncm",
            "kmod_usbg_storage",
            "kmod_usbg_stillimage",
            "kmod_usb_f_uvc",
            "kmod_usb_buspwr",
            "insmod_drv2",
            "usb_insmod_sh",
        }
        self.assertEqual(set(fx.keys()), expected_keys)
        self.assertTrue(all(len(v) > 0 for v in fx.values()))

    # --- Pillar 1: No-UVC Gadget Stack, Network Streaming & USB-LAN ---

    def test_11_pillar1_fx3_uvc_unmasked_rejected(self) -> None:
        res = evaluate_nouvc_gadget_and_network_streaming(
            body_model="ILME-FX3",
            requested_usb_mode="USB_STREAMING",
            stage_b_mask_uvc=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.native_uvc_supported)
        self.assertTrue(res.uvc_gadget_rejected)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

    def test_12_pillar1_fx3a_uvc_unmasked_rejected(self) -> None:
        res = evaluate_nouvc_gadget_and_network_streaming(
            body_model="ILME-FX3A",
            requested_usb_mode="USB_STREAMING",
            stage_b_mask_uvc=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.model_id_hex, "0x91030082")
        self.assertTrue(res.uvc_gadget_rejected)

    def test_13_pillar1_fx3_stage_b_uvc_masked_prevents_phy_lockup(self) -> None:
        res = evaluate_nouvc_gadget_and_network_streaming(
            body_model="ILME-FX3",
            requested_usb_mode="USB_STREAMING",
            stage_b_mask_uvc=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.uvc_masked_by_stage_b)
        self.assertTrue(res.usb_phy_lockup_prevented)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)

    def test_14_pillar1_fx30_fx2_fx6_native_uvc_allowed(self) -> None:
        for model, hex_id in (
            ("ILME-FX30", "0x91030081"),
            ("ILME-FX2", "0x91030085"),
            ("ILME-FX6", "0x91030060"),
        ):
            res = evaluate_nouvc_gadget_and_network_streaming(
                body_model=model,
                requested_usb_mode="USB_STREAMING",
                stage_b_mask_uvc=False,
            )
            self.assertTrue(res.valid, f"{model} failed")
            self.assertTrue(res.native_uvc_supported)
            self.assertEqual(res.model_id_hex, hex_id)
            self.assertEqual(res.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_15_pillar1_remote_shooting_legacy_1024x576_no_audio_cap(self) -> None:
        res = evaluate_nouvc_gadget_and_network_streaming(
            body_model="ILME-FX3",
            requested_usb_mode="REMOTE_SHOOTING",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.legacy_imaging_edge_cap, "1024x576_NO_AUDIO")

    def test_16_pillar1_network_streaming_rtmp_rtmps_srt_4k5994_38mbps(self) -> None:
        for proto in ("RTMP", "RTMPS", "SRT"):
            res = evaluate_nouvc_gadget_and_network_streaming(
                body_model="ILME-FX3",
                requested_usb_mode="USB_LAN",
                streaming_protocol=proto,
                streaming_width=3840,
                streaming_height=2160,
                streaming_fps=59.94,
                streaming_bitrate_mbps=38.0,
                streaming_codec="HEVC",
                usb_lan_auto_connect=True,
                usb_lan_driver="CDC_NCM",
            )
            self.assertTrue(res.valid, proto)
            self.assertTrue(res.usb_lan_auto_connect_702)
            self.assertEqual(res.streaming_resolution, "3840x2160")

    def test_17_pillar1_streaming_bitrate_over_38mbps_rejected(self) -> None:
        res = evaluate_nouvc_gadget_and_network_streaming(
            body_model="ILME-FX3",
            requested_usb_mode="USB_LAN",
            streaming_protocol="SRT",
            streaming_bitrate_mbps=42.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("38MBPS" in e for e in res.errors))

    def test_18_pillar1_streaming_fps_and_res_over_cap_rejected(self) -> None:
        res_fps = evaluate_nouvc_gadget_and_network_streaming(streaming_fps=120.0)
        res_res = evaluate_nouvc_gadget_and_network_streaming(streaming_width=4096)
        self.assertFalse(res_fps.valid)
        self.assertFalse(res_res.valid)

    def test_19_pillar1_boot_insmod_proves_zero_uvc_autoload(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
        p1 = rep.pillar_1_nouvc_streaming
        self.assertTrue(p1.passed)
        self.assertFalse(p1.uvc_loaded_in_boot_insmod)
        self.assertTrue(p1.kmod_cdc_ncm.modinfo_valid)
        self.assertTrue(p1.kmod_usbg_storage.modinfo_valid)
        self.assertTrue(p1.kmod_usbg_stillimage.modinfo_valid)
        self.assertTrue(p1.kmod_usb_f_uvc.modinfo_valid)

    def test_20_pillar1_unknown_body_or_protocol_rejected(self) -> None:
        r_body = evaluate_nouvc_gadget_and_network_streaming(body_model="ILME-FX9")
        r_proto = evaluate_nouvc_gadget_and_network_streaming(streaming_protocol="WEBRTC")
        self.assertFalse(r_body.valid)
        self.assertFalse(r_proto.valid)

    # --- Pillar 2: Power-Delivery Matrix (USB-PD vs DC-C1) ---

    def test_21_pillar2_body_pd_with_np_fz100_on_pauses_charging(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="BODY_USBC_PD",
            np_fz100_inserted=True,
            pd_adapter_watts=27.0,
            camera_powered_on=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.power_accepted)
        self.assertTrue(res.charging_paused_during_operation)
        self.assertFalse(res.internal_charging_active)
        self.assertFalse(res.brownout_shutdown_risk)

    def test_22_pillar2_body_pd_with_np_fz100_off_resumes_charging(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="BODY_USBC_PD",
            np_fz100_inserted=True,
            pd_adapter_watts=27.0,
            camera_powered_on=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.internal_charging_active)
        self.assertFalse(res.charging_paused_during_operation)

    def test_23_pillar2_body_pd_without_np_fz100_rejected_even_at_100w(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="BODY_USBC_PD",
            np_fz100_inserted=False,
            pd_adapter_watts=100.0,
            cable_current_rating_a=5.0,
            cable_has_emarker=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.power_accepted)
        self.assertTrue(res.brownout_shutdown_risk)

    def test_24_pillar2_body_pd_under_18w_rejected(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="BODY_USBC_PD",
            np_fz100_inserted=True,
            pd_adapter_watts=10.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("INSUFFICIENT_USB_PD_WATTS" in e for e in res.errors))

    def test_25_pillar2_micro_usb_power_strictly_rejected(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="MICRO_USB",
            np_fz100_inserted=True,
            pd_adapter_watts=15.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.micro_usb_power_rejected)
        self.assertFalse(res.power_accepted)

    def test_26_pillar2_dcc1_65w_5a_emarker_accepted_and_frees_type_c(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="DC_C1_COUPLER",
            np_fz100_inserted=False,
            pd_adapter_watts=65.0,
            cable_current_rating_a=5.0,
            cable_has_emarker=True,
            camera_powered_on=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.power_accepted)
        self.assertTrue(res.type_c_freed_for_usblan)
        self.assertTrue(res.lcd_max_brightness_locked)
        self.assertFalse(res.dcc1_led_blinking_warning)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_27_pillar2_dcc1_under_65w_rejected_with_blink_warning(self) -> None:
        res = evaluate_power_delivery_matrix(
            power_source="DC_C1_COUPLER",
            pd_adapter_watts=45.0,
            cable_current_rating_a=5.0,
            cable_has_emarker=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.dcc1_led_blinking_warning)
        self.assertTrue(res.brownout_shutdown_risk)

    def test_28_pillar2_dcc1_missing_emarker_or_3a_cable_rejected(self) -> None:
        res_no_em = evaluate_power_delivery_matrix(
            power_source="DC_C1_COUPLER",
            pd_adapter_watts=100.0,
            cable_current_rating_a=5.0,
            cable_has_emarker=False,
        )
        res_3a = evaluate_power_delivery_matrix(
            power_source="DC_C1_COUPLER",
            pd_adapter_watts=100.0,
            cable_current_rating_a=3.0,
            cable_has_emarker=True,
        )
        self.assertFalse(res_no_em.valid)
        self.assertFalse(res_3a.valid)
        self.assertTrue(res_no_em.dcc1_led_blinking_warning)
        self.assertTrue(res_3a.dcc1_led_blinking_warning)

    def test_29_pillar2_internal_battery_only_checks_presence(self) -> None:
        ok = evaluate_power_delivery_matrix(power_source="INTERNAL_BATTERY_ONLY", np_fz100_inserted=True)
        bad = evaluate_power_delivery_matrix(power_source="INTERNAL_BATTERY_ONLY", np_fz100_inserted=False)
        self.assertTrue(ok.valid)
        self.assertTrue(ok.type_c_freed_for_usblan)
        self.assertFalse(bad.valid)

    def test_30_pillar2_unknown_power_source_rejected(self) -> None:
        res = evaluate_power_delivery_matrix(power_source="DTAP_UNREGULATED")
        self.assertFalse(res.valid)
        self.assertTrue(res.brownout_shutdown_risk)

    # --- Pillar 3: Dual-Media LUT Path Asymmetry, .cube, Cine EI, RMT-P1BT & Cloud ---

    def test_31_pillar3_sd_requires_private_sony_pro_lut(self) -> None:
        ok = evaluate_user_lut_path_and_cine_ei(
            media_type="SD",
            submitted_dir=SD_USER_LUT_DIR_P192,
        )
        bad = evaluate_user_lut_path_and_cine_ei(
            media_type="SD",
            submitted_dir=CFEXPRESS_A_USER_LUT_DIR_P192,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.path_asymmetry_ok)
        self.assertFalse(bad.valid)
        self.assertFalse(bad.path_asymmetry_ok)

    def test_32_pillar3_cfexpress_requires_root_sony_pro_lut_without_private(self) -> None:
        ok = evaluate_user_lut_path_and_cine_ei(
            media_type="CFEXPRESS_A",
            submitted_dir=CFEXPRESS_A_USER_LUT_DIR_P192,
        )
        bad = evaluate_user_lut_path_and_cine_ei(
            media_type="CFEXPRESS_A",
            submitted_dir=SD_USER_LUT_DIR_P192,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.path_asymmetry_ok)
        self.assertFalse(bad.valid)
        self.assertFalse(bad.path_asymmetry_ok)

    def test_33_pillar3_cube_filename_63_byte_ascii_limit(self) -> None:
        ok_63 = ("X" * 58) + ".cube"  # 63 bytes
        bad_64 = ("X" * 59) + ".cube"  # 64 bytes
        res_ok = evaluate_user_lut_path_and_cine_ei(cube_filename=ok_63)
        res_bad = evaluate_user_lut_path_and_cine_ei(cube_filename=bad_64)
        res_utf8 = evaluate_user_lut_path_and_cine_ei(cube_filename="胶片LUT.cube")
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.filename_ascii_bytes, 63)
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_utf8.valid)

    def test_34_pillar3_cube_text_17pt_validation_and_malformed_rejects(self) -> None:
        ok_txt = _make_cube_17_text()
        ok, sz, vox, errs = validate_cube_text_bounded(ok_txt)
        self.assertTrue(ok)
        self.assertEqual(sz, 17)
        self.assertEqual(vox, 4913)
        self.assertEqual(errs, ())

        nan_ok, _, _, nan_errs = validate_cube_text_bounded(_make_cube_17_text("nan 0.5 0.5"))
        self.assertFalse(nan_ok)
        self.assertIn("NON_FINITE_CUBE_VOXEL", nan_errs)

        oned_ok, _, _, oned_errs = validate_cube_text_bounded("LUT_1D_SIZE 1024\n0.0 0.0 0.0\n")
        self.assertFalse(oned_ok)
        self.assertIn("UNSUPPORTED_1D_CUBE_LUT", oned_errs)

    def test_35_pillar3_cube_text_integration_with_evaluator(self) -> None:
        ok_txt = _make_cube_17_text()
        res = evaluate_user_lut_path_and_cine_ei(
            media_type="CFEXPRESS_A",
            submitted_dir="/Sony/PRO/LUT/",
            cube_filename="Valid17.cube",
            lut_3d_size=17,
            cube_text=ok_txt,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.cube_voxel_count, 4913)

        mismatch = evaluate_user_lut_path_and_cine_ei(
            lut_3d_size=33,
            cube_text=ok_txt,
        )
        self.assertFalse(mismatch.valid)

    def test_36_pillar3_user_lut_slots_1_to_16_and_ae_offset_thirds(self) -> None:
        for slot in (1, 16):
            for thirds in (0, 1, 6):
                res = evaluate_user_lut_path_and_cine_ei(
                    user_lut_slot=slot,
                    ae_level_offset_thirds=thirds,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.user_lut_slot, f"User{slot}")
        self.assertFalse(evaluate_user_lut_path_and_cine_ei(user_lut_slot=0).valid)
        self.assertFalse(evaluate_user_lut_path_and_cine_ei(user_lut_slot=17).valid)
        self.assertFalse(evaluate_user_lut_path_and_cine_ei(ae_level_offset_thirds=7).valid)
        self.assertFalse(evaluate_user_lut_path_and_cine_ei(ae_level_offset_thirds=-1).valid)

    def test_37_pillar3_cine_ei_dual_base_800_and_12800_no_cmos_gain_shift(self) -> None:
        low_ok = evaluate_user_lut_path_and_cine_ei(cine_ei_base_iso=800, cine_ei_index=200)
        high_ok = evaluate_user_lut_path_and_cine_ei(cine_ei_base_iso=12800, cine_ei_index=51200)
        self.assertTrue(low_ok.valid)
        self.assertTrue(high_ok.valid)
        self.assertFalse(low_ok.cmos_analog_gain_polluted)
        self.assertFalse(high_ok.cmos_analog_gain_polluted)

        bad_low = evaluate_user_lut_path_and_cine_ei(cine_ei_base_iso=800, cine_ei_index=12800)
        bad_high = evaluate_user_lut_path_and_cine_ei(cine_ei_base_iso=12800, cine_ei_index=800)
        bad_base = evaluate_user_lut_path_and_cine_ei(cine_ei_base_iso=1600, cine_ei_index=1600)
        self.assertFalse(bad_low.valid)
        self.assertFalse(bad_high.valid)
        self.assertFalse(bad_base.valid)

    def test_38_pillar3_stage_b_p2_setting_direct_write_blocked(self) -> None:
        res = evaluate_user_lut_path_and_cine_ei(
            stage_b_target_path="p2:/setting/UserLut1.bin",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.persistent_writes, 0)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

    def test_39_pillar3_rmt_p1bt_bt_on_disables_ir_and_gps(self) -> None:
        res = evaluate_rmt_p1bt_and_clip_flag_matrix(
            body_model="ILME-FX3",
            bluetooth_rmt_ctrl_on=True,
            ir_remote_requested=True,
            gps_link_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.bt_ir_gps_mutual_exclusion_enforced)
        self.assertFalse(res.effective_ir_remote_active)
        self.assertFalse(res.effective_gps_link_active)
        self.assertTrue(res.hardware_ir_present)
        self.assertTrue(res.hardware_nfc_present)

    def test_40_pillar3_rmt_p1bt_bt_off_allows_ir_on_fx3_but_not_fx3a(self) -> None:
        fx3 = evaluate_rmt_p1bt_and_clip_flag_matrix(
            body_model="ILME-FX3",
            bluetooth_rmt_ctrl_on=False,
            ir_remote_requested=True,
            gps_link_requested=True,
        )
        fx3a = evaluate_rmt_p1bt_and_clip_flag_matrix(
            body_model="ILME-FX3A",
            bluetooth_rmt_ctrl_on=False,
            ir_remote_requested=True,
            gps_link_requested=True,
        )
        self.assertTrue(fx3.effective_ir_remote_active)
        self.assertTrue(fx3.effective_gps_link_active)
        self.assertFalse(fx3a.hardware_ir_present)
        self.assertFalse(fx3a.hardware_nfc_present)
        self.assertFalse(fx3a.effective_ir_remote_active)
        self.assertTrue(fx3a.effective_gps_link_active)

    def test_41_pillar3_creators_cloud_version_gate_and_clip_flags(self) -> None:
        for flag in ("NONE", "OK", "NG", "KEEP", "ALL"):
            res = evaluate_rmt_p1bt_and_clip_flag_matrix(
                creators_app_version="3.1.0",
                monitor_control_version="2.4.0",
                clip_flag_filter=flag,
            )
            self.assertTrue(res.valid, flag)
            self.assertTrue(res.cloud_version_gate_ok)

        old_ca = evaluate_rmt_p1bt_and_clip_flag_matrix(creators_app_version="3.0.9")
        old_mc = evaluate_rmt_p1bt_and_clip_flag_matrix(monitor_control_version="2.3.5")
        bad_flag = evaluate_rmt_p1bt_and_clip_flag_matrix(clip_flag_filter="FAVORITE")
        self.assertFalse(old_ca.valid)
        self.assertFalse(old_mc.valid)
        self.assertFalse(bad_flag.valid)

    # --- Pillar 4: Hard Write Firewall & 12-Touchpoint 4-Class Matrix ---

    def test_42_pillar4_write_guard_blocks_all_persistent_targets(self) -> None:
        forbidden = (
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "/dev/mmcblk0p2",
            "p2:/setting/Backup.bin",
            "p2:/setting/UserLut.bin",
            "p8:/cpapp-b.bin",
            "BODYDATA.DAT",
            "spi_nor:loader_nor.bin",
            "/etc/arbitrary_unlisted",
        )
        for tgt in forbidden:
            wg = evaluate_phase192_write_guard(tgt)
            self.assertFalse(wg.valid, f"expected blocked: {tgt}")
            self.assertTrue(wg.persistent_write_blocked)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertFalse(wg.spi_nor_write_authorized)
            self.assertFalse(wg.el3_payload_transmit_authorized)
            self.assertEqual(wg.physical_usb_packets_emitted, 0)
            self.assertEqual(wg.persistent_writes, 0)

    def test_43_pillar4_write_guard_allows_volatile_and_ext_media(self) -> None:
        allowed = (
            "/tmp/stage_b/nouvc.json",
            "/tmp_wbshd/lut_cache.json",
            "ram://user_lut_slot1",
            "memfd:overlay",
            "/mnt/sd/Private/Sony/PRO/LUT/A.cube",
            "/mnt/cfexpress_a/Sony/PRO/LUT/B.cube",
        )
        for tgt in allowed:
            wg = evaluate_phase192_write_guard(tgt)
            self.assertTrue(wg.valid, f"expected allowed: {tgt}")
            self.assertTrue(wg.volatile_or_ext_allowed)
            self.assertEqual(wg.persistent_writes, 0)

    def test_44_pillar4_compat_matrix_has_12_touchpoints_and_all_4_classes(self) -> None:
        mat = build_phase192_compat_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertEqual(len(mat.touchpoints), 12)
        for bcls in VALID_BRIDGE_CLASSES:
            self.assertGreater(mat.class_counts[bcls], 0, f"missing class {bcls}")
        self.assertEqual(sum(mat.class_counts.values()), 12)
        self.assertEqual(sum(mat.pillar_counts.values()), 12)

    def test_45_pillar_reports_all_passed(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=True)
        self.assertTrue(rep.nouvc_and_network_streaming_verified)
        self.assertTrue(rep.power_delivery_pd_vs_dcc1_verified)
        self.assertTrue(rep.lut_path_cine_ei_and_rmt_p1bt_verified)
        self.assertTrue(rep.write_firewall_and_matrix_verified)
        self.assertEqual(rep.errors, ())

    def test_46_cli_subcommand_clean_room_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-nouvc-dcc1-lut-cineei", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema_version"], PHASE_192_SCHEMA)
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_47_cli_subcommand_auto_mode_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-nouvc-dcc1-lut-cineei", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_48_run_audit_all_registers_40_of_40_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("realhw_nouvc_dcc1_pd_lut_path_cineei_audit", summary)
        audit_keys = [k for k in summary.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 40)
        self.assertTrue(summary["realhw_nouvc_dcc1_pd_lut_path_cineei_audit"]["all_checks_passed"])

    def test_49_report_to_dict_roundtrip_json_serializable(self) -> None:
        rep = analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(clean_room=False)
        d = realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict(rep)
        encoded = json.dumps(d, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertEqual(decoded["pillar_4_write_guard_matrix"]["compatibility_matrix"]["total_touchpoints"], 12)

    def test_50_evaluate_lut_unsupported_media_rejected(self) -> None:
        res = evaluate_user_lut_path_and_cine_ei(media_type="SSD_USB")
        self.assertFalse(res.valid)
        self.assertFalse(res.path_asymmetry_ok)

    def test_51_evaluate_lut_unsupported_3d_size_rejected(self) -> None:
        res = evaluate_user_lut_path_and_cine_ei(lut_3d_size=65)
        self.assertFalse(res.valid)
        self.assertEqual(res.cube_voxel_count, 0)

    def test_52_evaluate_rmt_p1bt_unsupported_body_rejected(self) -> None:
        res = evaluate_rmt_p1bt_and_clip_flag_matrix(body_model="ILME-FX6")
        self.assertFalse(res.valid)


if __name__ == "__main__":
    unittest.main()
