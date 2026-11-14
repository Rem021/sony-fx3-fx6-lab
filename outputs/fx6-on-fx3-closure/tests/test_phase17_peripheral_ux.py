"""Phase 17 Dual-Mode Test Suite: Peripheral UX, Display Routing & Audio Compatibility.

Executes identically under both:
- Local read-only FX3/FX6 donor mode (`LOCAL_DONOR_AND_UNICORN_VERIFIED`)
- Clean-room synthetic ELF64 + AArch64 CI mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
"""

from __future__ import annotations

import os
import struct
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

from fx6_closure.elf_verify import PF_R, parse_elf64_aarch64
from fx6_closure.patcher import PatchVerificationError
from fx6_closure.peripheral_ux_compatibility_verifier import (
    FX6_KEYMAP_PAIR_COUNT,
    FX6_TP_SET_SIZE_PINNED_WORDS,
    INFRA_TP_QUEUE_ID,
    INFRA_TP_SET_TP_SIZE_VMA,
    P10_APPFW_KEYMAP_SPEC,
    PANELEVF_GET_OUTPUT_SEL_PINNED_WORDS,
    PANELEVF_GET_OUTPUT_SEL_VMA,
    apply_p10_keymap_adapter,
    audit_audio_and_hotshoe_compatibility,
    audit_display_routing_compatibility,
    audit_fx3_fx6_input_keymap,
    audit_touch_panel_compatibility,
    build_synthetic_clean_room_artifacts,
    is_forced_clean_room,
    resolve_phase17_donor_paths,
    rollback_p10_keymap_adapter,
    verify_peripheral_ux_compatibility,
)


class TestPhase17PeripheralUxCompatibility(unittest.TestCase):
    """Comprehensive positive & fault-injection suite for Phase 17 compatibility."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = verify_peripheral_ux_compatibility()
        cls.synth = build_synthetic_clean_room_artifacts()

    def test_01_end_to_end_verification_passes(self) -> None:
        """Full Phase 17 verification passes in the active mode (donor or clean-room)."""
        expected_mode = (
            "CLEAN_ROOM_SYNTHETIC_VERIFIED"
            if is_forced_clean_room()
            else "LOCAL_DONOR_AND_UNICORN_VERIFIED"
        )
        self.assertEqual(self.report.verification_mode, expected_mode)
        self.assertTrue(self.report.all_passed)
        self.assertEqual(self.report.schema_version, "17.0.0")

    def test_02_path_resolution_uses_home_and_forbids_external_volume_hardcode(self) -> None:
        """Verify dynamic Path.home() resolution, env override, and zero legacy hardcodes."""
        paths = resolve_phase17_donor_paths()
        expected_prefix = str(Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work")
        self.assertTrue(str(paths.fx6_lib_dir).startswith(expected_prefix))
        self.assertTrue(str(paths.fx3_lib_dir).startswith(expected_prefix))

        old_env = os.environ.get("FX3_FX6_WORK_ROOT")
        try:
            os.environ["FX3_FX6_WORK_ROOT"] = "/custom/work/root"
            overridden = resolve_phase17_donor_paths()
            self.assertTrue(str(overridden.fx6_lib_dir).startswith("/custom/work/root"))
        finally:
            if old_env is None:
                os.environ.pop("FX3_FX6_WORK_ROOT", None)
            else:
                os.environ["FX3_FX6_WORK_ROOT"] = old_env

        verifier_src = (
            Path(__file__).resolve().parents[1]
            / "fx6_closure"
            / "peripheral_ux_compatibility_verifier.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("/Volumes/" + "KAFU2T", verifier_src)

    def test_03_native_1to1_fx3_controls_and_menu_long_press(self) -> None:
        """Verify D-pad, ENTER, MENU (short & >=1000ms long press), REC, C5/C6, dials map 1:1."""
        ia = self.report.input_audit
        self.assertEqual(ia.native_1to1_count, 15)
        by_name = {r.fx3_button: r for r in ia.rows}
        self.assertEqual(by_name["UP"].unpatched_ev_on, 0x02010000)
        self.assertEqual(by_name["DOWN"].unpatched_ev_on, 0x02010003)
        self.assertEqual(by_name["LEFT"].unpatched_ev_on, 0x02010006)
        self.assertEqual(by_name["RIGHT"].unpatched_ev_on, 0x0201000B)
        self.assertEqual(by_name["ENTER"].unpatched_ev_on, 0x02010010)
        self.assertEqual(by_name["REC"].unpatched_ev_on, 0x02010101)
        self.assertEqual(by_name["C5"].unpatched_ev_on, 0x0201006A)
        self.assertEqual(by_name["C6"].unpatched_ev_on, 0x0201006C)
        self.assertEqual(by_name["MENU"].unpatched_ev_on, 0x02010015)
        self.assertEqual(by_name["MENU"].long_press_ms, 1000)
        self.assertEqual(by_name["MENU"].long_press_ev, 0x02010017)

    def test_04_unpatched_fx3_blind_spots_detected(self) -> None:
        """Confirm Fn, C1, C2, C3, PLAY, and DELETE have no active dispatch before P10."""
        ia = self.report.input_audit
        by_name = {r.fx3_button: r for r in ia.rows}
        for btn in ("Fn", "C1", "C2", "C3", "PLAY", "DELETE"):
            self.assertIsNone(by_name[btn].unpatched_ev_on, f"{btn} unexpectedly active unpatched")
        self.assertEqual(ia.unicorn_unpatched_fn_app_key, 0x8D)

    def test_05_p10_keymap_translation_enables_big6_home_and_back(self) -> None:
        """Verify P10 translates Fn->HOME (Big6), C1->KURU_PON, C2->MENU_CANCEL, C3->DISP_SEL."""
        ia = self.report.input_audit
        self.assertEqual(ia.p10_adapted_count, 6)
        self.assertEqual(ia.unicorn_p10_fn_app_key, 0x184)
        self.assertEqual(ia.unicorn_p10_c1_app_key, 0x029)
        self.assertEqual(ia.unicorn_p10_c2_app_key, 0x192)
        self.assertEqual(ia.unicorn_p10_c3_app_key, 0x199)
        self.assertEqual(ia.unicorn_p10_play_app_key, 0x183)
        self.assertEqual(ia.unicorn_p10_delete_app_key, 0x185)
        self.assertEqual(ia.unicorn_menu_app_key, 0x13)

        by_name = {r.fx3_button: r for r in ia.rows}
        self.assertEqual(by_name["Fn"].p10_ev_on, 0x020102D1)      # HOME / Big6
        self.assertEqual(by_name["C1"].p10_ev_on, 0x02010157)      # KURU_PON
        self.assertEqual(by_name["C2"].p10_ev_on, 0x02010107)      # MENU_CANCEL
        self.assertEqual(by_name["C3"].p10_ev_on, 0x020100E6)      # DISP_SEL
        self.assertEqual(by_name["PLAY"].p10_ev_on, 0x020100E9)    # THUMBNAIL
        self.assertEqual(by_name["DELETE"].p10_ev_on, 0x020102CB)  # USER

    def test_06_p10_patch_only_touches_pf_r_rodata_and_rolls_back_sha256_exact(self) -> None:
        """Prove P10 changes exactly 24 PF_R bytes and restores exact SHA-256 on rollback."""
        ia = self.report.input_audit
        self.assertEqual(ia.p10_patch_receipt.changed_byte_count, 24)
        self.assertTrue(ia.p10_rollback_receipt.donor_sha256_matched)
        self.assertEqual(ia.p10_rollback_receipt.restored_byte_count, 24)
        for site in P10_APPFW_KEYMAP_SPEC.sites:
            self.assertEqual(site.required_segment_flags, PF_R)

    def test_07_negative_p10_rejects_sha256_tamper_and_context_mismatch(self) -> None:
        """Fault injection: corrupted appFw.so SHA-256 or context fails P10 pre-check."""
        corrupted = bytearray(self.synth.appfw_bytes)
        corrupted[0x200] ^= 0xFF
        with self.assertRaises(PatchVerificationError):
            apply_p10_keymap_adapter(bytes(corrupted), spec=self.synth.p10_spec)

        patched, _ = apply_p10_keymap_adapter(self.synth.appfw_bytes, spec=self.synth.p10_spec)
        patched_mut = bytearray(patched)
        first_site = self.synth.p10_spec.sites[0]
        patched_mut[first_site.expected_file_offset] ^= 0x01
        with self.assertRaises(PatchVerificationError):
            rollback_p10_keymap_adapter(bytes(patched_mut), spec=self.synth.p10_spec)

    def test_08_synthetic_appfw_elf64_p10_unicorn_pipeline(self) -> None:
        """Verify synthetic clean-room AArch64 keymap ELF passes Unicorn + P10 end-to-end."""
        info = parse_elf64_aarch64(self.synth.appfw_bytes)
        self.assertEqual(len(info.load_segments), 2)
        audit = audit_fx3_fx6_input_keymap(
            self.synth.appfw_bytes,
            spec=self.synth.p10_spec,
            mode="UNITTEST_SYNTHETIC",
            synthetic_bundle=self.synth,
        )
        self.assertTrue(audit.passed)
        self.assertGreaterEqual(audit.keymap_pair_count, 1109)

    def test_09_touch_panel_uipc_protocol_and_unicorn_set_tp_size(self) -> None:
        """Verify libInfraTp.so (0x807b002b, /dev/tp) and Unicorn SetTpSize (1024x540 & bounds)."""
        ta = self.report.touch_audit
        self.assertTrue(ta.passed)
        self.assertTrue(ta.queue_id_match)
        self.assertTrue(ta.dev_node_match)
        self.assertTrue(ta.uipc_record_compatible)
        self.assertTrue(ta.prop_007a0001_modes_match)
        self.assertEqual(ta.unicorn_1024x540_rc, 1)
        self.assertEqual(ta.unicorn_1024x540_stored_size, (1024, 540))
        self.assertEqual(ta.unicorn_zero_width_rc, 0)
        self.assertEqual(ta.unicorn_negative_height_rc, 0)

    def test_10_negative_touch_panel_rejects_tampered_set_tp_size_insn(self) -> None:
        """Fault injection: mutating SetTpSize machine code triggers verification failure."""
        bad_tp = bytearray(self.synth.tp_bytes)
        struct.pack_into("<I", bad_tp, INFRA_TP_SET_TP_SIZE_VMA, 0xD503201F)  # nop
        with self.assertRaises(ValueError):
            audit_touch_panel_compatibility(bytes(bad_tp), mode="FAULT_INJECT")

    def test_11_display_routing_bk4_normalization_and_vari_angle_sensors(self) -> None:
        """Verify 0x02cf0214/0x02cf0218 1B vs 4B normalization & vari-angle LCD sensors."""
        da = self.report.display_audit
        self.assertTrue(da.passed)
        self.assertEqual(da.bk4_02cf0214_fx6_len, 1)
        self.assertEqual(da.bk4_02cf0214_fx3_len, 4)
        self.assertEqual(da.bk4_02cf0218_fx6_len, 1)
        self.assertEqual(da.bk4_02cf0218_fx3_len, 4)
        self.assertEqual(da.vari_angle_lcd_keys_mapped, 3)
        self.assertTrue(da.sdi_fpga_absent_handled)
        self.assertTrue(da.gpe_init_present)
        self.assertTrue(da.display_setup_anchors_present)

    def test_12_display_unicorn_get_output_sel_matrix(self) -> None:
        """Verify AVBB_SCN_START_PANELEVF GetOutputSel routes LCD (1), EVF (2), Mirror (3) safely."""
        da = self.report.display_audit
        self.assertEqual(da.unicorn_sel_lcd_vals, ((1, 1, 1), (3, 1, 1), (4, 1, 1)))
        self.assertEqual(da.unicorn_sel_evf_vals, ((2, 1, 2), (5, 1, 2)))
        self.assertEqual(da.unicorn_sel_mirror_val, (16, 1, 3))
        self.assertEqual(da.unicorn_sel_invalid_rc, 0)

    def test_13_negative_display_rejects_corrupted_get_output_sel(self) -> None:
        """Fault injection: corrupted GetOutputSel machine code fails display verifier."""
        bad_evf = bytearray(self.synth.scn_panelevf_bytes)
        struct.pack_into("<I", bad_evf, PANELEVF_GET_OUTPUT_SEL_VMA, 0xD503201F)
        with self.assertRaises(ValueError):
            audit_display_routing_compatibility(
                self.synth.appfw_bytes,
                bytes(bad_evf),
                self.synth.gpe_bytes,
                mode="FAULT_INJECT",
                synthetic_bundle=self.synth,
            )

    def test_14_negative_display_detects_missing_sdi_fallback_or_gpe(self) -> None:
        """Fault injection: missing SDI_OUTPUT_NOT_SUPPORT or GpeInit fails display audit."""
        bad_appfw = self.synth.appfw_bytes.replace(
            b"VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
            b"VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_BROKEN_XXXXX",
        )
        rep = audit_display_routing_compatibility(
            bad_appfw,
            self.synth.scn_panelevf_bytes,
            self.synth.gpe_bytes,
            mode="FAULT_INJECT",
            synthetic_bundle=self.synth,
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.sdi_fpga_absent_handled)

    def test_15_audio_xlr_h1_parity_and_event_driven_ch_dials(self) -> None:
        """Verify FX3 XLR-H1 F48B24C4_F96B24C2 parity and non-blocking CH1..4 dial dispatch."""
        aa = self.report.audio_audit
        self.assertTrue(aa.passed)
        self.assertTrue(aa.digmic_f48b24c4_parity)
        self.assertTrue(aa.xlr_h1_supported)
        self.assertTrue(aa.ch1_to_ch4_dials_event_driven_only)
        self.assertTrue(aa.p5_032d_contract_required)

    def test_16_audio_unicorn_hotshoe_wait_ok_and_timeout_graceful_fallback(self) -> None:
        """Verify WaitRecvCompMsgFromHotshoeRsrc returns 0 on ACK and 0x8000 safely on E_TMO."""
        aa = self.report.audio_audit
        self.assertEqual(aa.unicorn_wait_ok_rc, 0)
        self.assertTrue(aa.unicorn_wait_ok_freed_msg)
        self.assertEqual(aa.unicorn_wait_timeout_rc, 0x8000)
        self.assertTrue(aa.unicorn_wait_timeout_nonblocking)

    def test_17_negative_audio_detects_missing_xlr_h1_or_dial_event(self) -> None:
        """Fault injection: missing DIGITAL_XLR or corrupt CH1 dial event fails audio audit."""
        bad_appfw = self.synth.appfw_bytes.replace(
            b"VAL_connect_shoe_mic_CONNECT_SHOE_MIC_DIGITAL_XLR",
            b"VAL_connect_shoe_mic_CONNECT_SHOE_MIC_UNKNOWN_XXX",
        )
        rep = audit_audio_and_hotshoe_compatibility(
            bad_appfw,
            self.synth.hotshoe_bytes,
            mode="FAULT_INJECT",
            synthetic_bundle=self.synth,
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.xlr_h1_supported)

    def test_18_report_serialization_and_donor_or_cleanroom_constants(self) -> None:
        """Verify report JSON serialization and pinned keymap/touch/display constants."""
        as_dict = self.report.to_dict()
        self.assertTrue(as_dict["all_passed"])
        self.assertIn("input_audit", as_dict)
        self.assertIn("touch_audit", as_dict)
        self.assertIn("display_audit", as_dict)
        self.assertIn("audio_audit", as_dict)
        self.assertEqual(FX6_KEYMAP_PAIR_COUNT, 1115)
        self.assertEqual(INFRA_TP_QUEUE_ID, 0x807B002B)
        self.assertEqual(len(FX6_TP_SET_SIZE_PINNED_WORDS), 8)
        self.assertEqual(len(PANELEVF_GET_OUTPUT_SEL_PINNED_WORDS), 22)


if __name__ == "__main__":
    unittest.main()
