#!/usr/bin/env python3
"""Unit tests for Phase 328 (Stage 69 — 69/69 Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-59:
Ver. 7.00/7.02 `HOME` (`BIG6`) Screen (`Mode Settings = Fixed/Variable`, 4-State Machine,
Dynamic 6 Tiles, Metadata-Only `[Home (Lower Left)]` `ND Filter` with Zero Physical e-ND)
& Active Manual `[Framing Settings]` vs Dormant AI `[Auto Framing]` (`EOPNOTSUPP=95`),
Still-Only `[Interval Shoot Func.]` (All 7 Sub-Items Resettable, `Slot-1` `EROFS=30`/`EBUSY=16`
Vault Firewall) vs `ILME-FX6` Single-MXF `Interval Rec`,
`[Time Code Make]` (`Regenerate` -> `Slot 1` Under `Simult. Recording` + Forced `Rec Run`,
`VMC-BNCM1` `EXT-LK`, Zero `Clock` Mode) & `[HDMI Output Settings]` (`[REC Control]` Across
`Rec. Media = On` & `Off(HDMI Only)`, `[4ch Audio Output]` 2ch HDMI Limit), and
Ver. 7.00+ `[Access Authen. Settings]` (SSH Tunnel `sshd_start` + Host Key Fingerprint +
PTP-IP, Zero `HTTP_DIGEST`/`BASIC_AUTH`/`HTTPS`, Outbound Client TLS `[Import Root
Certificate]`, Zero-RF `Airplane Mode`) & `[Fan Control]` (4-Mode FX3 vs 3-Mode FX6,
Zero `Max` Mode on Both Cameras) + `[Auto Power OFF Temp.]` (`Initialize`-Only) HIL
(94 dual-mode tests).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_big6_home_framing_interval_tc_ssh_fan_coemulator as p328  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..68 for quick Stage 69 isolation tests."""
    base = dict(
        force_clean_room=True,
        include_phase41_dtb_mhlx=False,
        include_phase45_imx510_xavc=False,
        include_phase53_hil_fault_harness=False,
        include_phase58_qmp_introspection=False,
        include_phase63_hdmi_raw_uvc=False,
        include_phase67_tc_lens_paint=False,
        include_phase71_dualslot_ups_salvage=False,
        include_phase78_touchaf_ciz_assignable=False,
        include_phase82_camset_lpcm_tcub=False,
        include_phase87_playback_shotmark_dewpoint=False,
        include_phase91_gyroflow_rtmd_anamorphic=False,
        include_phase96_interval_cache_ftp_fan=False,
        include_phase99_lut3d_subzero_sdi=False,
        include_phase103_emi_exfat_endurance=False,
        include_phase107_c2pa_shading_mcfleet_ovp=False,
        include_phase112_hdr_hlg_fiz_gimbal=False,
        include_phase117_proresraw_breathing_mishoe_hil=False,
        include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        include_phase132_vp_ledwall_freed_artnet_hil=False,
        include_phase141_realhw_preflash_dualboot_hil=False,
        include_phase145_realhw_mpr_dmm_rec=False,
        include_phase150_realhw_body_peripheral_hil=False,
        include_phase157_realhw_imx510_network_usb_hil=False,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
        include_phase167_realhw_cxd90058_sabin_seal_hil=False,
        include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
        include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
        include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
        include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
        include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
        include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
        include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
        include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=False,
        include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=False,
        include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=False,
        include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=False,
        include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=False,
        include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=False,
        include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=False,
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
        include_stage49=False,
        include_stage50=False,
        include_stage51=False,
        include_stage52=False,
        include_stage53=False,
        include_stage54=False,
        include_stage55=False,
        include_stage56=False,
        include_stage57=False,
        include_stage58=False,
        include_stage59=False,
        include_stage60=False,
        include_stage61=False,
        include_stage62=False,
        include_stage63=False,
        include_stage64=False,
        include_stage65=False,
        include_stage66=False,
        include_stage67=False,
        include_stage68=False,
    )
    base.update(overrides)
    return base


_FAST_CLI_FLAGS = [
    "--clean-room",
    "--skip-phase41",
    "--skip-phase45",
    "--skip-phase53",
    "--skip-phase58",
    "--skip-phase63",
    "--skip-phase67",
    "--skip-phase71",
    "--skip-phase78",
    "--skip-phase82",
    "--skip-phase87",
    "--skip-phase91",
    "--skip-phase96",
    "--skip-phase99",
    "--skip-phase103",
    "--skip-phase107",
    "--skip-phase112",
    "--skip-phase117",
    "--skip-phase121",
    "--skip-phase127",
    "--skip-phase132",
    "--skip-phase141",
    "--skip-phase145",
    "--skip-phase150",
    "--skip-phase157",
    "--skip-phase162",
    "--skip-phase167",
    "--skip-phase172",
    "--skip-phase178",
    "--skip-phase182",
    "--skip-phase188",
    "--skip-phase194",
    "--skip-phase200",
    "--skip-phase202",
    "--skip-phase207",
    "--skip-phase213",
    "--skip-phase217",
    "--skip-phase222",
    "--skip-phase226",
    "--skip-phase232",
    "--skip-phase236",
    "--skip-stage44",
    "--skip-stage45",
    "--skip-stage46",
    "--skip-stage47",
    "--skip-stage48",
    "--skip-stage49",
    "--skip-stage50",
    "--skip-stage51",
    "--skip-stage52",
    "--skip-stage53",
    "--skip-stage54",
    "--skip-stage55",
    "--skip-stage56",
    "--skip-stage57",
    "--skip-stage58",
    "--skip-stage59",
    "--skip-stage60",
    "--skip-stage61",
    "--skip-stage62",
    "--skip-stage63",
    "--skip-stage64",
    "--skip-stage65",
    "--skip-stage66",
    "--skip-stage67",
    "--skip-stage68",
]


class TestRealHwStage69Big6HomeFramingIntervalTcSshFan(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & Dual-Mode Tests (Tests 1..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_69_of_69(self) -> None:
        self.assertEqual(p328.PHASE_NUMBER, 328)
        self.assertEqual(p328.STAGE_INDEX, 69)
        self.assertEqual(p328.STAGE_TOTAL, 69)
        self.assertEqual(p328.MILESTONE_LABEL, "69/69")
        self.assertTrue(p328.IS_69TH_STAGE_MILESTONE)
        self.assertEqual(p328.STAGE_NAME, "stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil")
        self.assertEqual(len(p328.DONOR_RELPATHS), 24)
        self.assertEqual(len(p328.EXPECTED_DONOR_BYTES), 24)
        self.assertEqual(len(p328.EXPECTED_COMPACT_DONOR_SHA256), 21)
        self.assertEqual(len(p328.EXPECTED_LARGE_HEAD4K_SHA256), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p328.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p328.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p328.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p328.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p328.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p328.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p328.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p328.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p328.FX3_HAS_BUILTIN_END_FILTER)
        self.assertTrue(p328.FX6_HAS_ELECTRONIC_VARIABLE_ND)
        self.assertFalse(p328.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p328.ELECTRONIC_ND_COMMANDS_EMITTED, 0)
        self.assertEqual(p328.RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(p328.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p328.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p328.clean_room_test_mode(env={}))
        self.assertTrue(p328.clean_room_test_mode(env={p328.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p328.clean_room_test_mode(env={p328.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p328.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p328.clean_room_test_mode(
                force_clean_room=False,
                env={p328.ENV_FORCE_CLEAN_ROOM: "1", p328.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_sentinel_and_donorless_fallback_no_typeerror(self) -> None:
        self.assertIsNone(
            p328.resolve_mac_work_root(
                env={p328.ENV_MAC_WORK_ROOT: p328.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p328.resolve_mac_work_root(
                env={p328.ENV_MAC_ROOT: p328.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p328, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p328, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p328.resolve_mac_work_root(env={}))
                    rep = p328.run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p328.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_24_contracts(self) -> None:
        for env_key in (p328.ENV_FORCE_CLEAN_ROOM, p328.ENV_CLEAN_ROOM_TEST):
            audit = p328.inspect_phase328_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p328.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p328.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 24)
            self.assertEqual(audit.compact_donors_verified, 21)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p328.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p328._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p328.inspect_phase328_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p328.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 24)
        self.assertEqual(audit.compact_donors_verified, 21)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_libssh2_donor_sha256_and_size_verified(self) -> None:
        self.assertEqual(p328.EXPECTED_DONOR_BYTES["fx3_lib_ssh2"], 216_784)
        self.assertEqual(
            p328.EXPECTED_COMPACT_DONOR_SHA256["fx3_lib_ssh2"],
            "5dc7ca0687907bc6f4b7938000a934a7fa8cd8122c31950c682e5147964cee0c",
        )
        self.assertIn(b"libssh2", p328.COMPACT_DONOR_TOKENS["fx3_lib_ssh2"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p328._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p328.Stage69Phase328Error):
                p328._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p328.Stage69Phase328Error):
                p328._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p328.Stage69Phase328Error):
                p328._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p328.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p328._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p328.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_lib_ssh2"] = "0" * 64
            with unittest.mock.patch.object(
                p328, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p328.inspect_phase328_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn("digest_or_size_mismatch:fx3_lib_ssh2", audit.verification_notes)
        finally:
            p328._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p328.run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase328_payload_passes_clean_room(self) -> None:
        rep = p328.run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p328.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "69/69")
        self.assertTrue(rep["is_69th_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase328_payload_passes_local_donor_mode(self) -> None:
        if p328.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p328.run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p328.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 24)

    def test_13_fx3_large_windows_contain_wave59_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p328.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "BKID_FPS_FIXED_VAR",
            "BKID_HOME_SCREEN_STATE",
            "UPDATE_BIG6_ITEM_ISO_EI",
            "BKID_HOME_LOWER_LEFT",
            "SWIPE_DOWN_HOME_SCREEN",
            "EFRAMING_MANUAL_ONLY",
            "BKID_FRAMING_SETTINGS",
            "BKID_INTERVAL_SHOOT",
            "VAL_TC_MAKE_REGENRATE",
            "PRM_HAITA_REC_CONTROL",
            "BKID_HDMI_AUDIO_4CH",
            "BKID_FAN_CONTROL",
            "BKID_AUTO_PWR_OFF_TEMP",
            "BKID_ACCESS_AUTHEN",
            "SSHD_START_CMD",
            "SSHD_START_SYM",
            "FAN_CONTROL_ALWAYS_OFF",
            "ROOT_CERT_CLOUD",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_large_windows_contain_wave59_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p328.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "FX6_BIG6_HOME_PRESENTER",
            "FX6_TC_MAKE_CLOCK",
            "FX6_INTERVAL_REC_EXCLUSION",
            "FX6_FAN_ALWAYS_OFF",
            "FX6_SDI_HDMI_REC_CTRL",
            "FX6_AUTO_FRAMING",
        ):
            self.assertIn(expected, labels)

    # ------------------------------------------------------------------
    # Sub-Model 69A — BIG6 HOME Screen & Manual Framing vs Dormant AI Auto Framing (Tests 15..36)
    # ------------------------------------------------------------------

    def test_15_fx3_big6_admitted_in_ver700_and_ver702_with_fixed_var(self) -> None:
        for fw in (p328.FW_VER_700, p328.FW_VER_702):
            res = p328.simulate_big6_home_and_framing_hil(
                firmware_version=fw,
                mode_settings=p328.FX3_MODE_SETTINGS_FIXED_VAR,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.errno_code, 0)
            self.assertEqual(res.home_screen_state, "HOME_SCREEN_STATE_ON_CURSOR_OFF")

    def test_16_fx3_big6_blocked_in_ver601(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            firmware_version=p328.FW_VER_601,
            mode_settings=p328.FX3_MODE_SETTINGS_FIXED_VAR,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.home_screen_state, "HOME_SCREEN_STATE_OFF")

    def test_17_fx3_big6_blocked_in_flexible_exp_and_pasm_iauto(self) -> None:
        for mode in (p328.FX3_MODE_SETTINGS_FLEX_EXP, "P", "A", "S", "M", "Intelligent Auto"):
            res = p328.simulate_big6_home_and_framing_hil(
                firmware_version=p328.FW_VER_702,
                mode_settings=mode,
            )
            self.assertFalse(res.admitted, mode)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.home_screen_state, "HOME_SCREEN_STATE_OFF")

    def test_18_fx3_big6_swipe_down_requires_touch_operation_on(self) -> None:
        ok = p328.simulate_big6_home_and_framing_hil(
            entry_trigger="Swipe Down",
            touch_operation="On",
        )
        self.assertTrue(ok.admitted)
        blocked = p328.simulate_big6_home_and_framing_hil(
            entry_trigger="Swipe Down",
            touch_operation="Off",
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.errno_code, p328.EOPNOTSUPP_ERRNO)
        home_key_ok = p328.simulate_big6_home_and_framing_hil(
            entry_trigger="HOME Custom Key",
            touch_operation="Off",
        )
        self.assertTrue(home_key_ok.admitted)

    def test_19_fx3_big6_4state_machine_and_last_cursor_position(self) -> None:
        s_on = p328.simulate_big6_home_and_framing_hil(
            cursor_selected=False, open_menu_or_fn_overlay=False, last_cursor_position=3
        )
        self.assertEqual(s_on.home_screen_state, "HOME_SCREEN_STATE_ON_CURSOR_OFF")
        self.assertEqual(s_on.last_cursor_position, 3)

        s_csr = p328.simulate_big6_home_and_framing_hil(
            cursor_selected=True, open_menu_or_fn_overlay=False, last_cursor_position=4
        )
        self.assertEqual(s_csr.home_screen_state, "HOME_SCREEN_STATE_ON_CURSOR_ON")

        s_tmp = p328.simulate_big6_home_and_framing_hil(
            cursor_selected=True, open_menu_or_fn_overlay=True
        )
        self.assertEqual(s_tmp.home_screen_state, "HOME_SCREEN_STATE_TEMP_OFF")

    def test_20_fx3_big6_dynamic_6_tiles_cine_ei_and_shutter_angle(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            log_shooting="Cine EI",
            shutter_mode="Angle",
            fps_fps=60,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(len(res.tiles), 6)
        self.assertIn("60p", res.tiles["tile_1_fps"])
        self.assertIn("Base ISO 800 / EI 800", res.tiles["tile_2_iso_ei"])
        self.assertIn("Shutter Angle", res.tiles["tile_3_shutter"])
        self.assertIn("Aperture", res.tiles["tile_4_lower_left"])
        self.assertIn("Select LUT", res.tiles["tile_5_pp_lut"])

    def test_21_fx3_big6_iso_speed_pp_when_log_off(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            log_shooting="Off",
            shutter_mode="Speed",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.tiles["tile_2_iso_ei"], "ISO 800")
        self.assertIn("Shutter Speed", res.tiles["tile_3_shutter"])
        self.assertIn("Picture Profile", res.tiles["tile_5_pp_lut"])

    def test_22_fx3_big6_lower_left_nd_filter_metadata_only_zero_end(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            home_lower_left_setting="ND Filter",
            nd_filter_label="ND16",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.home_lower_left_setting, "ND Filter")
        self.assertTrue(res.nd_tile_metadata_only)
        self.assertFalse(res.fx3_has_builtin_end_filter)
        self.assertEqual(res.electronic_nd_commands_emitted, 0)
        self.assertIn("Metadata-Only", res.tiles["tile_4_lower_left"])

    def test_23_fx3_big6_edge_status_bar_readonly_never_over_hdmi_sdi(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil()
        self.assertTrue(res.edge_status_bar_readonly)
        self.assertEqual(res.hdmi_sdi_status_bar_leaked_pixels, 0)

    def test_24_fx3_camera_settings_reset_restores_aperture_and_fixed_var_and_framing_off(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            mode_settings=p328.FX3_MODE_SETTINGS_FLEX_EXP,
            home_lower_left_setting="ND Filter",
            framing_enabled=True,
            framing_rec_stream_output="Crop",
            framing_hdmi_output="Full",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.mode_settings, p328.FX3_MODE_SETTINGS_FIXED_VAR)
        self.assertEqual(res.home_lower_left_setting, "Aperture")
        self.assertFalse(res.framing_enabled)
        self.assertEqual(res.framing_rec_stream_output, "Full")
        self.assertEqual(res.framing_hdmi_output, "Crop")

    def test_25_fx6_native_home_screen_has_real_variable_electronic_nd(self) -> None:
        for nd_mode in p328.FX6_HOME_ND_MODES:
            res = p328.simulate_big6_home_and_framing_hil(
                body_profile=p328.BODY_MODEL_FX6,
                firmware_version=p328.FW_VER_601,
                nd_filter_label=nd_mode,
                log_shooting="Cine EI",
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.nd_tile_metadata_only)
            self.assertTrue(res.fx6_has_electronic_variable_nd)
            self.assertIn(f"Electronic ND ({nd_mode})", res.tiles["tile_4_nd_iris"])

    def test_26_fx3_manual_framing_settings_auto_disables_apsc_s35(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            framing_enabled=True,
            framing_rec_stream_output="Crop",
            framing_hdmi_output="Full",
            apsc_s35_requested=True,
            fps_fps=60,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.framing_enabled)
        self.assertEqual(res.framing_rec_stream_output, "Crop")
        self.assertEqual(res.framing_hdmi_output, "Full")
        self.assertTrue(res.apsc_s35_forced_off)

    def test_27_fx3_manual_framing_locked_at_100p_and_120p(self) -> None:
        for fps in (100, 120):
            res = p328.simulate_big6_home_and_framing_hil(
                framing_enabled=True,
                fps_fps=fps,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_28_fx3_manual_framing_menu_locked_during_rec_or_streaming(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            framing_enabled=True,
            is_recording_or_streaming=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EBUSY_ERRNO)

    def test_29_fx6_lacks_fx3_manual_framing_settings(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            body_profile=p328.BODY_MODEL_FX6,
            firmware_version=p328.FW_VER_601,
            framing_enabled=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_30_dormant_ai_auto_framing_rejected_on_both_fx3_and_fx6(self) -> None:
        for body in p328.VALID_BODY_MODELS:
            res = p328.simulate_big6_home_and_framing_hil(
                body_profile=body,
                auto_framing_requested=True,
            )
            self.assertFalse(res.admitted, body)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_auto_framing_rejected)

    def test_31_dormant_auto_framing_catalog_contains_5_items(self) -> None:
        self.assertEqual(
            p328.DORMANT_AUTO_FRAMING_ITEMS,
            (
                "Auto Framing",
                "Auto Framing Settings",
                "Crop Level",
                "Framing Tracking Speed",
                "Framing Stabilizer",
            ),
        )

    def test_32_69a_invalid_cursor_position_raises_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_big6_home_and_framing_hil(last_cursor_position=6)

    def test_33_69a_invalid_lower_left_raises_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_big6_home_and_framing_hil(home_lower_left_setting="Shutter")

    def test_34_69a_invalid_body_or_fw_raises_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_big6_home_and_framing_hil(body_profile="ILME-FX3A")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_big6_home_and_framing_hil(firmware_version="5.00")

    def test_35_69a_fx6_temp_off_overlay_state(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(
            body_profile=p328.BODY_MODEL_FX6,
            firmware_version=p328.FW_VER_601,
            open_menu_or_fn_overlay=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.home_screen_state, "HOME_SCREEN_STATE_TEMP_OFF")

    def test_36_69a_fx3_cine_ei_quick_also_uses_base_iso_ei_tile(self) -> None:
        res = p328.simulate_big6_home_and_framing_hil(log_shooting="Cine EI Quick")
        self.assertTrue(res.admitted)
        self.assertEqual(res.tiles["tile_2_iso_ei"], "Base ISO 800 / EI 800")

    # ------------------------------------------------------------------
    # Sub-Model 69B — Still-Only `[Interval Shoot Func.]` & Slot-1 Vault vs FX6 (Tests 37..54)
    # ------------------------------------------------------------------

    def test_37_interval_shoot_7_subitems_catalog(self) -> None:
        self.assertEqual(len(p328.FX3_INTERVAL_7_SUBITEMS), 7)
        self.assertEqual(
            p328.FX3_INTERVAL_7_SUBITEMS,
            (
                "Interval Shooting",
                "Shooting Start Time",
                "Shooting Interval",
                "Number of Shots",
                "AE Tracking Sensitivity",
                "Shutter Type in Interval",
                "Shoot Interval Priority",
            ),
        )

    def test_38_interval_shoot_still_slot2_up_to_19998_raw_plus_heif(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            number_of_shots=9999,
            still_file_format="RAW & HEIF",
            bulb_requested=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.expected_dcim_file_count, 19_998)
        self.assertTrue(res.exited_bulb_to_30s)
        self.assertFalse(res.in_body_movie_muxed)
        self.assertEqual(res.shutter_type_in_interval, "Electronic Shutter")

    def test_39_interval_shoot_single_format_9999_files(self) -> None:
        for fmt in ("JPEG", "HEIF", "RAW"):
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                target_slot=p328.SLOT_2,
                recording_media_mode="Slot 2",
                number_of_shots=9999,
                still_file_format=fmt,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.expected_dcim_file_count, 9999)

    def test_40_interval_shoot_all_7_subitems_resettable_via_camera_settings_reset(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            interval_shooting="On",
            shooting_start_time_s=300,
            shooting_interval_s=45,
            number_of_shots=1200,
            ae_tracking_sensitivity="High",
            shutter_type_in_interval="Mechanical Shutter",
            shoot_interval_priority="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.interval_shooting, "Off")
        self.assertEqual(res.shooting_start_time_s, 1)
        self.assertEqual(res.shooting_interval_s, 3)
        self.assertEqual(res.number_of_shots, 30)
        self.assertEqual(res.ae_tracking_sensitivity, "Mid")
        self.assertEqual(res.shutter_type_in_interval, "Electronic Shutter")
        self.assertEqual(res.shoot_interval_priority, "Off")
        self.assertEqual(res.expected_dcim_file_count, 0)

    def test_41_interval_shoot_rejects_in_body_movie_muxing(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            in_body_movie_mux_requested=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.in_body_movie_muxed)

    def test_42_interval_shoot_rejects_movie_and_sq_modes(self) -> None:
        for mode in (p328.SHOOT_MODE_MOVIE, p328.SHOOT_MODE_SQ):
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                shoot_mode=mode,
                target_slot=p328.SLOT_2,
                recording_media_mode="Slot 2",
            )
            self.assertFalse(res.admitted, mode)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_43_interval_shoot_blocked_in_intelligent_auto(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            exposure_mode="Intelligent Auto",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_44_interval_shoot_bounds_validation_einval(self) -> None:
        for kwargs in (
            dict(shooting_start_time_s=0),
            dict(shooting_start_time_s=6000),
            dict(shooting_interval_s=0),
            dict(shooting_interval_s=61),
            dict(number_of_shots=0),
            dict(number_of_shots=10_000),
        ):
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                target_slot=p328.SLOT_2,
                recording_media_mode="Slot 2",
                **kwargs,
            )
            self.assertFalse(res.admitted, str(kwargs))
            self.assertEqual(res.errno_code, p328.EINVAL_ERRNO)

    def test_45_slot1_tier0_vault_firewall_blocks_slot1_and_simult(self) -> None:
        for slot, media in (
            (p328.SLOT_1, "Slot 1"),
            (p328.SLOT_2, "Simult. Recording"),
        ):
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                target_slot=slot,
                recording_media_mode=media,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p328.EROFS_ERRNO)
            self.assertTrue(res.tier0_vault_firewall_triggered)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_46_slot1_tier0_vault_ebusy_when_busy(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_1,
            recording_media_mode="Slot 1",
            vault_busy=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EBUSY_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_triggered)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_47_fx6_interval_rec_single_xavc_mxf_clip(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            body_profile=p328.BODY_MODEL_FX6,
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            fx6_interval_time_s=86_400,
            fx6_number_of_frames=24,
            fx6_pre_lighting="10s",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.still_file_format, "XAVC_MXF")
        self.assertTrue(res.in_body_movie_muxed)
        self.assertEqual(res.expected_dcim_file_count, 1)

    def test_48_fx6_interval_rec_all_4_mutual_exclusions_ebusy(self) -> None:
        for conflict in p328.FX6_INTERVAL_REC_EXCLUSIONS:
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                body_profile=p328.BODY_MODEL_FX6,
                target_slot=p328.SLOT_2,
                recording_media_mode="Slot 2",
                fx6_concurrent_conflict=conflict,
            )
            self.assertFalse(res.admitted, conflict)
            self.assertEqual(res.errno_code, p328.EBUSY_ERRNO)

    def test_49_fx6_interval_rec_canceled_on_video_format_change(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            body_profile=p328.BODY_MODEL_FX6,
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            fx6_video_format_changed=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.interval_shooting, "Off")

    def test_50_fx6_interval_rec_invalid_frames_or_time_einval(self) -> None:
        for time_s, frames in ((0, 3), (86_401, 3), (10, 5), (10, 25)):
            res = p328.simulate_interval_shoot_and_slot1_vault_hil(
                body_profile=p328.BODY_MODEL_FX6,
                target_slot=p328.SLOT_2,
                recording_media_mode="Slot 2",
                fx6_interval_time_s=time_s,
                fx6_number_of_frames=frames,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p328.EINVAL_ERRNO)

    def test_51_fx6_slot1_interval_also_blocked_by_tier0_vault(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            body_profile=p328.BODY_MODEL_FX6,
            target_slot=p328.SLOT_1,
            recording_media_mode="Slot 1",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EROFS_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_triggered)

    def test_52_69b_invalid_args_raise_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_interval_shoot_and_slot1_vault_hil(target_slot=3)
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_interval_shoot_and_slot1_vault_hil(still_file_format="TIFF")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_interval_shoot_and_slot1_vault_hil(
                shutter_type_in_interval="Global"
            )

    def test_53_69b_mechanical_shutter_supported_when_configured(self) -> None:
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_2,
            recording_media_mode="Slot 2",
            shutter_type_in_interval="Mechanical Shutter",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.shutter_type_in_interval, "Mechanical Shutter")

    def test_54_69b_reset_with_slot1_still_triggers_vault_only_if_on_false_allows_off(self) -> None:
        # Reset turns interval_shooting="Off"; no write is issued on Slot 1 when Off
        res = p328.simulate_interval_shoot_and_slot1_vault_hil(
            target_slot=p328.SLOT_1,
            recording_media_mode="Slot 1",
            interval_shooting="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.interval_shooting, "Off")
        self.assertEqual(res.slot1_data_sector_writes, 0)

    # ------------------------------------------------------------------
    # Sub-Model 69C — `[Time Code Make/Run]` & `[HDMI Output Settings]` (Tests 55..70)
    # ------------------------------------------------------------------

    def test_55_tc_regenerate_under_simult_reads_slot1_and_forces_rec_run(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            recording_media_mode="Simult. Recording",
            tc_make="Regenerate",
            tc_run="Free Run",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.regenerate_reference_slot, p328.SLOT_1)
        self.assertEqual(res.effective_tc_make, "Regenerate")
        self.assertEqual(res.effective_tc_run, "Rec Run")

    def test_56_tc_regenerate_slot2_reads_slot2_and_other_modes_read_slot1(self) -> None:
        s2 = p328.simulate_tc_make_run_and_hdmi_output_hil(
            recording_media_mode="Slot 2",
            tc_make="Regenerate",
            tc_run="Free Run",
        )
        self.assertEqual(s2.regenerate_reference_slot, p328.SLOT_2)
        self.assertEqual(s2.effective_tc_run, "Rec Run")

        for media in ("Slot 1", "Sort Recording", "Relay Recording"):
            s1 = p328.simulate_tc_make_run_and_hdmi_output_hil(
                recording_media_mode=media,
                tc_make="Regenerate",
            )
            self.assertEqual(s1.regenerate_reference_slot, p328.SLOT_1, media)

    def test_57_tc_and_hdmi_are_initialize_only_survive_camera_settings_reset(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            tc_make="Regenerate",
            tc_run="Free Run",
            rec_media_during_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            hdmi_4ch_audio_output="CH3/CH4",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_tc_make, "Regenerate")
        self.assertEqual(res.rec_media_during_hdmi_output, "Off(HDMI Only)")
        self.assertEqual(res.time_code_output, "On")
        self.assertTrue(res.rec_control_active)
        self.assertEqual(res.hdmi_4ch_audio_output, "CH3/CH4")

    def test_58_initialize_resets_tc_and_hdmi_output_to_defaults(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            tc_make="Regenerate",
            tc_run="Free Run",
            rec_media_during_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            hdmi_4ch_audio_output="CH3/CH4",
            initialize_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_tc_make, "Preset")
        self.assertEqual(res.effective_tc_run, "Rec Run")
        self.assertEqual(res.rec_media_during_hdmi_output, "On")
        self.assertEqual(res.time_code_output, "Off")
        self.assertFalse(res.rec_control_active)
        self.assertEqual(res.hdmi_4ch_audio_output, "CH1/CH2")

    def test_59_vmc_bncm1_ext_lk_requires_preset_plus_free_run_unmodified(self) -> None:
        ok = p328.simulate_tc_make_run_and_hdmi_output_hil(
            tc_make="Preset",
            tc_run="Free Run",
            vmc_bncm1_connected=True,
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.ext_lk_locked)

        for bad_kwargs in (
            dict(tc_make="Regenerate", tc_run="Free Run"),
            dict(tc_make="Preset", tc_run="Rec Run"),
            dict(tc_make="Preset", tc_run="Free Run", preset_edited_while_extlk=True),
        ):
            bad = p328.simulate_tc_make_run_and_hdmi_output_hil(
                vmc_bncm1_connected=True,
                **bad_kwargs,
            )
            self.assertFalse(bad.admitted, str(bad_kwargs))
            self.assertEqual(bad.errno_code, p328.EOPNOTSUPP_ERRNO)
            self.assertFalse(bad.ext_lk_locked)

    def test_60_fx3_rejects_clock_tc_make_unlike_fx6(self) -> None:
        fx3 = p328.simulate_tc_make_run_and_hdmi_output_hil(
            body_profile=p328.BODY_MODEL_FX3,
            tc_make="Clock",
        )
        self.assertFalse(fx3.admitted)
        self.assertEqual(fx3.errno_code, p328.EOPNOTSUPP_ERRNO)

        fx6 = p328.simulate_tc_make_run_and_hdmi_output_hil(
            body_profile=p328.BODY_MODEL_FX6,
            tc_make="Clock",
        )
        self.assertTrue(fx6.admitted)
        self.assertTrue(fx6.ext_lk_locked)

    def test_61_hdmi_rec_control_requires_time_code_output_on(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            time_code_output="Off",
            rec_control="On",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.rec_control_active)

    def test_62_hdmi_rec_control_active_in_both_rec_media_on_and_hdmi_only(self) -> None:
        on_rec = p328.simulate_tc_make_run_and_hdmi_output_hil(
            rec_media_during_hdmi_output="On",
            time_code_output="On",
            rec_control="On",
            is_recording=True,
        )
        self.assertTrue(on_rec.admitted)
        self.assertTrue(on_rec.rec_control_active)
        self.assertEqual(on_rec.hdmi_status_indicator, "(REC)")

        hdmi_only_stby = p328.simulate_tc_make_run_and_hdmi_output_hil(
            rec_media_during_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            is_recording=False,
        )
        self.assertTrue(hdmi_only_stby.admitted)
        self.assertTrue(hdmi_only_stby.rec_control_active)
        self.assertEqual(hdmi_only_stby.hdmi_status_indicator, "(STBY)")

    def test_63_hdmi_rec_control_and_tc_output_blocked_in_sq_mode(self) -> None:
        for kwargs in (
            dict(time_code_output="On", rec_control="Off"),
            dict(time_code_output="On", rec_control="On"),
        ):
            res = p328.simulate_tc_make_run_and_hdmi_output_hil(
                shoot_mode=p328.SHOOT_MODE_SQ,
                **kwargs,
            )
            self.assertFalse(res.admitted, str(kwargs))
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_64_hdmi_rec_control_blocked_during_streaming_ebusy(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            time_code_output="On",
            rec_control="On",
            streaming_active=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EBUSY_ERRNO)
        self.assertFalse(res.rec_control_active)

    def test_65_hdmi_4ch_audio_output_ch12_vs_ch34_strict_2ch_limit(self) -> None:
        for ch_pair in p328.VALID_HDMI_4CH_AUDIO_MODES:
            res = p328.simulate_tc_make_run_and_hdmi_output_hil(
                hdmi_4ch_audio_output=ch_pair,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.hdmi_4ch_audio_output, ch_pair)
            self.assertEqual(res.hdmi_audio_channels_carried, 2)

    def test_66_fx6_sdi_hdmi_remote_if_and_parallel_rec_modes(self) -> None:
        for mode in p328.VALID_FX6_REC_CTRL_MODES:
            res = p328.simulate_tc_make_run_and_hdmi_output_hil(
                body_profile=p328.BODY_MODEL_FX6,
                fx6_sdi_hdmi_rec_ctrl_mode=mode,
                is_recording=True,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.fx6_sdi_hdmi_rec_ctrl_mode, mode)
            if mode == "Off":
                self.assertFalse(res.rec_control_active)
            else:
                self.assertTrue(res.rec_control_active)
                self.assertEqual(res.hdmi_status_indicator, "(REC)")

    def test_67_69c_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_tc_make_run_and_hdmi_output_hil(tc_make="Invalid")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_tc_make_run_and_hdmi_output_hil(hdmi_4ch_audio_output="CH1-4")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_tc_make_run_and_hdmi_output_hil(
                rec_media_during_hdmi_output="Dual"
            )

    def test_68_69c_sq_allows_hdmi_when_tc_and_rec_ctrl_off(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            shoot_mode=p328.SHOOT_MODE_SQ,
            rec_media_during_hdmi_output="Off(HDMI Only)",
            time_code_output="Off",
            rec_control="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.rec_media_during_hdmi_output, "On")

    def test_69_69c_hdmi_rec_ctrl_off_leaves_indicator_off(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            time_code_output="On",
            rec_control="Off",
            is_recording=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.rec_control_active)
        self.assertEqual(res.hdmi_status_indicator, "Off")

    def test_70_69c_fx6_regenerate_also_forces_rec_run_slot1(self) -> None:
        res = p328.simulate_tc_make_run_and_hdmi_output_hil(
            body_profile=p328.BODY_MODEL_FX6,
            tc_make="Regenerate",
            tc_run="Free Run",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_tc_run, "Rec Run")
        self.assertEqual(res.regenerate_reference_slot, 1)

    # ------------------------------------------------------------------
    # Sub-Model 69D — `[Access Authen. Settings]` (SSH + PTP-IP) & `[Fan Control]` / Temp (Tests 71..84)
    # ------------------------------------------------------------------

    def test_71_access_authen_ssh_tunnel_and_ptpip_admitted(self) -> None:
        res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="On",
            auth_protocol="SSH_TUNNEL_PTPIP",
            wifi_security="WPA3-SAE",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_access_authen, "On")
        self.assertTrue(res.sshd_started)
        self.assertTrue(res.ssh_host_key_fingerprint_verified)
        self.assertEqual(res.airplane_mode, "On")
        self.assertEqual(res.rf_packets_transmitted, 0)

    def test_72_access_authen_rejects_http_digest_basic_https(self) -> None:
        for proto in p328.UNSUPPORTED_ACCESS_AUTH_PROTOCOLS:
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(auth_protocol=proto)
            self.assertFalse(res.admitted, proto)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.sshd_started)

    def test_73_wifi_rejects_removed_wep_wpa_psk_ipsec_allows_wpa2_wpa3(self) -> None:
        for bad in p328.REMOVED_WIFI_SECURITY:
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(wifi_security=bad)
            self.assertFalse(res.admitted, bad)
            self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)
        for good in p328.SUPPORTED_WIFI_SECURITY:
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(wifi_security=good)
            self.assertTrue(res.admitted, good)

    def test_74_import_root_cert_outbound_client_only_for_cloud_ftp_rtmp(self) -> None:
        for ctype in p328.VALID_ROOT_CERT_TYPES:
            ok = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
                root_cert_type=ctype,
                root_cert_imported=True,
            )
            self.assertTrue(ok.admitted, ctype)
            self.assertTrue(ok.root_cert_outbound_client_only)
            self.assertTrue(ok.root_cert_present)

        bad = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            root_cert_inbound_server_requested=True,
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_75_access_authen_and_cert_survive_cam_reset_cleared_by_network_reset_or_init(self) -> None:
        cam_rst = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="Off",
            root_cert_imported=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(cam_rst.admitted)
        self.assertEqual(cam_rst.effective_access_authen, "Off")
        self.assertFalse(cam_rst.sshd_started)
        self.assertTrue(cam_rst.root_cert_present)

        net_rst = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="Off",
            root_cert_imported=True,
            reset_network_set_applied=True,
        )
        self.assertEqual(net_rst.effective_access_authen, "On")
        self.assertTrue(net_rst.sshd_started)
        self.assertFalse(net_rst.root_cert_present)

        init_rst = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            access_authen_setting="Off",
            root_cert_imported=True,
            initialize_applied=True,
        )
        self.assertEqual(init_rst.effective_access_authen, "On")
        self.assertFalse(init_rst.root_cert_present)

    def test_76_airplane_mode_stays_on_and_zero_rf_across_both_resets(self) -> None:
        for flags in (
            dict(airplane_mode="Off", reset_network_set_applied=True),
            dict(airplane_mode="Off", initialize_applied=True),
            dict(airplane_mode="On", camera_settings_reset_applied=True),
        ):
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(**flags)
            self.assertTrue(res.admitted)
            self.assertEqual(res.airplane_mode, "On")
            self.assertEqual(res.rf_packets_transmitted, 0)
            self.assertEqual(res.rf_nvs_mutation_bytes, 0)

    def test_77_fx3_supports_4_fan_control_modes(self) -> None:
        self.assertEqual(len(p328.FX3_FAN_CONTROL_MODES), 4)
        for mode in p328.FX3_FAN_CONTROL_MODES:
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
                body_profile=p328.BODY_MODEL_FX3,
                fan_control_mode=mode,
            )
            self.assertTrue(res.admitted, mode)
            self.assertEqual(res.effective_fan_control_mode, mode)

    def test_78_fx6_supports_3_fan_modes_and_rejects_always_off(self) -> None:
        self.assertEqual(len(p328.FX6_FAN_CONTROL_MODES), 3)
        for mode in p328.FX6_FAN_CONTROL_MODES:
            res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
                body_profile=p328.BODY_MODEL_FX6,
                fan_control_mode=mode,
            )
            self.assertTrue(res.admitted, mode)
            self.assertEqual(res.effective_fan_control_mode, mode)

        always_off = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            body_profile=p328.BODY_MODEL_FX6,
            fan_control_mode="Always Off",
        )
        self.assertFalse(always_off.admitted)
        self.assertEqual(always_off.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_79_neither_fx3_nor_fx6_has_fan_control_max_mode(self) -> None:
        for body in p328.VALID_BODY_MODELS:
            for max_mode in p328.DORMANT_FAN_CONTROL_MODES:
                res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
                    body_profile=body,
                    fan_control_mode=max_mode,
                )
                self.assertFalse(res.admitted, f"{body}:{max_mode}")
                self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_80_fan_off_in_rec_engages_thermal_override_at_65c(self) -> None:
        cool = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            fan_control_mode="Off in Rec",
            sensor_temp_c=45,
        )
        self.assertFalse(cool.fan_thermal_override_engaged)

        hot = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            fan_control_mode="Off in Rec",
            sensor_temp_c=65,
        )
        self.assertTrue(hot.admitted)
        self.assertTrue(hot.fan_thermal_override_engaged)

    def test_81_auto_power_off_temp_standard_vs_high_and_burn_advisory(self) -> None:
        std = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            auto_power_off_temp="Standard", ambient_temp_c=25
        )
        self.assertEqual(std.estimated_4k60_limit_min_25c, 30)
        self.assertFalse(std.low_temp_burn_advisory)

        hi = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            auto_power_off_temp="High", ambient_temp_c=25
        )
        self.assertEqual(hi.estimated_4k60_limit_min_25c, 90)
        self.assertTrue(hi.low_temp_burn_advisory)

    def test_82_fan_control_and_auto_temp_are_initialize_only(self) -> None:
        net_rst = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            fan_control_mode="Always Off",
            auto_power_off_temp="High",
            reset_network_set_applied=True,
        )
        self.assertEqual(net_rst.effective_fan_control_mode, "Always Off")
        self.assertEqual(net_rst.effective_auto_power_off_temp, "High")

        init_rst = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            fan_control_mode="Always Off",
            auto_power_off_temp="High",
            initialize_applied=True,
        )
        self.assertEqual(init_rst.effective_fan_control_mode, "Auto")
        self.assertEqual(init_rst.effective_auto_power_off_temp, "Standard")

    def test_83_fx6_lacks_consumer_auto_power_off_temp_high(self) -> None:
        res = p328.simulate_access_auth_ssh_and_fan_thermal_hil(
            body_profile=p328.BODY_MODEL_FX6,
            auto_power_off_temp="High",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p328.EOPNOTSUPP_ERRNO)

    def test_84_69d_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_access_auth_ssh_and_fan_thermal_hil(access_authen_setting="Maybe")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_access_auth_ssh_and_fan_thermal_hil(root_cert_type="SSH")
        with self.assertRaises(p328.Stage69Phase328Error):
            p328.simulate_access_auth_ssh_and_fan_thermal_hil(auto_power_off_temp="Ultra")

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 69 Wiring (Tests 85..94)
    # ------------------------------------------------------------------

    def test_85_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_big6_home_framing_interval_tc_ssh_fan_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("69/69", proc.stdout)

    def test_86_suite_cli_help_percent_escaping_and_stage69_flags(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("69/69 Milestone", proc.stdout)
        self.assertIn("--include-stage69", proc.stdout)
        self.assertIn("--skip-stage69", proc.stdout)
        self.assertIn("--no-include-stage69", proc.stdout)
        self.assertIn("--skip-phase328", proc.stdout)

    def test_87_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p328.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 328 Stage 69 (69/69 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p328.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "69/69")
        self.assertTrue(parsed["is_69th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_88_no_hardcoded_usr_bin_python3_in_stage69_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_big6_home_framing_interval_tc_ssh_fan_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_89_suite_default_config_enables_stage69_and_full_run_contains_69_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase328_realhw_big6_home_framing_interval_tc_ssh_fan_hil)
        self.assertTrue(cfg.include_stage69)
        self.assertTrue(cfg.stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil)

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 69)
        s69 = rep["stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil"]
        self.assertTrue(s69["all_checks_passed"])
        self.assertTrue(s69["is_69th_stage_milestone"])
        self.assertEqual(s69["milestone"], "69/69")
        self.assertEqual(s69["phase_number"], 328)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_90_suite_skip_flags_and_summary_cli_for_stage69(self) -> None:
        for flag in ("--skip-stage69", "--no-include-stage69", "--skip-phase328"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage69"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage69", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_big6_home_framing_interval_tc_ssh_fan_hil=CLEAN_ROOM_SYNTHETIC("
            "m69=69/69,end_tx=0,afram_byp=0,ivl_mux=0,fan_max=0,rf_tx=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_91_suite_tamper_end_auto_framing_interval_mux_detected(self) -> None:
        for attr, val in (
            ("ELECTRONIC_ND_COMMANDS_EMITTED", 1),
            ("DORMANT_AUTO_FRAMING_EXPOSED_EVENTS", 1),
            ("FRAMING_HIGHFPS_OR_REC_BYPASS_EVENTS", 1),
            ("INTERVAL_INBODY_MOVIE_MUX_EVENTS", 1),
            ("INTERVAL_IAUTO_OR_BULB_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p328, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_slot1_vault_or_tc_clock_or_hdmi_detected(self) -> None:
        for attr, val in (
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("SLOT1_VAULT_INTERVAL_WRITE_EVENTS", 1),
            ("TC_REGEN_NON_SLOT1_OR_FREERUN_VIOLATIONS", 1),
            ("FX3_CLOCK_TC_MAKE_EXPOSED_EVENTS", 1),
            ("HDMI_REC_CTRL_S_AND_Q_OR_NOTC_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p328, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_suite_tamper_ssh_wep_fan_max_or_rf_tx_detected(self) -> None:
        for attr, val in (
            ("SSH_HTTP_BASIC_HTTPS_AUTH_SPOOF_EVENTS", 1),
            ("REMOVED_WEP_WPA_IPSEC_EXPOSED_EVENTS", 1),
            ("FAN_CONTROL_MAX_EXPOSED_EVENTS", 1),
            ("FX6_FAN_ALWAYS_OFF_EXPOSED_EVENTS", 1),
            ("RF_PACKETS_TRANSMITTED", 1),
            ("RF_NVS_MUTATION_BYTES", 16),
        ):
            with unittest.mock.patch.object(p328, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_94_stage69_all_redline_zero_keys_verified(self) -> None:
        rep = p328.run_phase328_big6_home_framing_interval_tc_ssh_fan_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        for zero_key in (
            "nop_count",
            "guest_code_modification_bytes",
            "cp_mutation_bytes",
            "wbi_mutation_bytes",
            "calibration_mutation_bytes",
            "cnflasha_mutation_bytes",
            "nvram_persistent_writes",
            "bk4_persistent_nvram_writes",
            "physical_device_writes",
            "emmc_nflasha_write_count",
            "electronic_nd_commands_emitted",
            "hdmi_sdi_status_bar_leaked_pixels",
            "dormant_auto_framing_exposed_events",
            "framing_highfps_or_rec_bypass_events",
            "interval_inbody_movie_mux_events",
            "interval_iauto_or_bulb_bypass_events",
            "slot1_data_sector_writes",
            "slot1_vault_interval_write_events",
            "tc_regen_non_slot1_or_freerun_violations",
            "fx3_clock_tc_make_exposed_events",
            "hdmi_rec_ctrl_s_and_q_or_notc_bypass_events",
            "ssh_http_basic_https_auth_spoof_events",
            "removed_wep_wpa_ipsec_exposed_events",
            "fan_control_max_exposed_events",
            "fx6_fan_always_off_exposed_events",
            "rf_packets_transmitted",
            "rf_nvs_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)


if __name__ == "__main__":
    unittest.main()
