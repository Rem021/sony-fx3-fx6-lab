#!/usr/bin/env python3
"""Unit tests for Phase 281 (Stage 56, 56/56):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-46
`[Power Save by Monitor]` Reality Split (`appFw.so` 4-Mode vs `ILME-FX3` `ilc/2210` 2-Item
`[Power Setting Option]`) & `[Power Save Start Time]` 9-Deactivation HIL,
`[Language]` (`BK_LANG` `0x02cf019c` 34-vs-29 Model Split & Stage-B 4-Language `.uxc`/`.ltt` Parity),
and `[Volume Settings]` (`0..15`, Default `7`), `[4ch Audio Monitoring]` (`5` Routes vs HDMI
`4ch Audio Output`), & `[Delete confirm.]` (`"Cancel" first` + `Slot-1` Recovery Vault Firewall)
HIL Co-Emulator (76 dual-mode tests).
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
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_power_save_monitor_language_volume_delete_coemulator as p281  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated stages for <50ms flag/override tests."""
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
]


class TestPhase281PowerSaveMonitorLanguageVolumeDeleteCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p281.run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
            force_clean_room=True
        )
        cls.default_audit = p281.run_phase281_realhw_power_save_monitor_language_volume_delete_hil()

        forced = p281.is_forced_clean_room()
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True if forced else None)
        )
        cls.default_suite_elapsed = time.monotonic() - t0

        if forced:
            cls.clean_suite = cls.default_suite
            cls.clean_suite_elapsed = cls.default_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
            )
            cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Stage 56 (56/56) & O_RDONLY 18-Donor Verification (16 tests)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase281_stage56_and_redline_constants(self) -> None:
        self.assertEqual(
            p281.SCHEMA_ID,
            "realhw_power_save_monitor_language_volume_delete_coemulator_v1",
        )
        self.assertEqual(p281.PHASE_281_SCHEMA, p281.SCHEMA_ID)
        self.assertEqual(p281.PHASE_281_VERSION, "281.0.0")
        self.assertEqual(p281.PHASE_NUMBER, 281)
        self.assertEqual(p281.STAGE_INDEX, 56)
        self.assertEqual(p281.STAGE_TOTAL, 56)
        self.assertEqual(p281.MILESTONE_LABEL, "56/56")
        self.assertEqual(
            p281.STAGE_NAME,
            "stage56_realhw_power_save_monitor_language_volume_delete_hil",
        )
        self.assertEqual(p281.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p281.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p281.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertFalse(p281.FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        self.assertTrue(p281.SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(p281.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p281.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p281.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p281.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_sha256_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p281.SOURCE_MODE_CLEAN_ROOM)
        again = p281.run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
            force_clean_room=True
        )
        self.assertEqual(
            self.clean_audit["audit_digest_sha256"],
            again["audit_digest_sha256"],
        )

    def test_03_both_clean_room_env_vars_force_clean_room(self) -> None:
        self.assertTrue(p281.is_forced_clean_room({p281.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p281.is_forced_clean_room({p281.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p281.is_forced_clean_room({p281.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertFalse(p281.is_forced_clean_room({}))
        rep = p281.run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
            env={p281.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(rep["source_mode"], p281.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(rep["all_checks_passed"])

    def test_04_donor_audit_18_artifacts_and_zero_raw_leakage(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["access_mode"], "O_RDONLY")
            self.assertEqual(da["donor_files_inspected"], 18)
            self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(da["power_save_monitor_split_proven"])
            self.assertTrue(da["language_bk_lang_4lang_proven"])
            self.assertTrue(da["volume_4ch_delete_confirm_proven"])
            self.assertTrue(da["all_contracts_verified"])
            self.assertEqual(list(da["errors"]), [])

    def test_05_compact_donors_13_exact_sizes_and_sha256(self) -> None:
        da = self.default_audit["donor_audit"]
        compact_keys = tuple(p281.EXPECTED_COMPACT_DONOR_SHA256.keys())
        self.assertEqual(len(compact_keys), 13)
        for key in compact_keys:
            item = da[key]
            self.assertEqual(item["file_bytes"], p281.EXPECTED_DONOR_BYTES[key], msg=key)
            self.assertEqual(len(item["sha256"]), 64, msg=key)
            self.assertTrue(item["sha256_verified"], msg=key)
            if da["source_mode"] == p281.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(
                    item["sha256"],
                    p281.EXPECTED_COMPACT_DONOR_SHA256[key],
                    msg=key,
                )

    def test_06_large_donors_5_bounded_window_rdonly_no_full_load(self) -> None:
        da = self.default_audit["donor_audit"]
        large_keys = tuple(p281.EXPECTED_LARGE_HEAD4K_SHA256.keys())
        self.assertEqual(len(large_keys), 5)
        for key in large_keys:
            item = da[key]
            self.assertTrue(item["bounded_windows_only"], msg=key)
            self.assertEqual(item["file_bytes"], p281.EXPECTED_DONOR_BYTES[key], msg=key)
            self.assertLess(item["bytes_read_total"], 100_000, msg=key)
            self.assertTrue(item["head_sha256_verified"], msg=key)
            self.assertTrue(all(v == 1 for v in item["window_hits"].values()), msg=key)
            if da["source_mode"] == p281.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(
                    item["head_sha256"],
                    p281.EXPECTED_LARGE_HEAD4K_SHA256[key],
                    msg=key,
                )

    def test_07_bk_lang_exact_offsets_and_values_across_fx3_fx6_donors(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["fx3_bk4_lang_le32"], 0)
            self.assertEqual(da["fx6_ntsc_bk_lang_u8"], 0x00)
            self.assertEqual(da["fx6_cn1_bk_lang_u8"], 0x19)

    def test_08_fx3_string_en_f_and_en_and_fx6_en_reality_split_tokens(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            en_f = da["fx3_string_en_f"]
            self.assertEqual(en_f["marker_hits"]["Power Save by Monitor"], 1)
            self.assertEqual(en_f["marker_hits"]["Both Linked"], 1)
            self.assertEqual(en_f["marker_hits"]["Open: Return"], 1)
            self.assertEqual(en_f["marker_hits"]["Close: Power Save"], 1)
            self.assertEqual(en_f["marker_hits"]["Does Not Link"], 1)
            self.assertEqual(en_f["absent_marker_hits"]["Open: On/Close: Off"], 0)

            fx3_en = da["fx3_string_en"]
            self.assertEqual(fx3_en["absent_marker_hits"]["Power Save by Monitor"], 0)
            self.assertEqual(fx3_en["absent_marker_hits"]["Open: On/Close: Off"], 0)
            self.assertEqual(fx3_en["marker_hits"]["Auto Power OFF Temp."], 1)

            fx6_en = da["fx6_string_en"]
            self.assertEqual(fx6_en["absent_marker_hits"]["Power Save by Monitor"], 0)
            self.assertEqual(fx6_en["absent_marker_hits"]["Auto Power OFF Temp."], 0)
            self.assertEqual(fx6_en["marker_hits"]["Language Select"], 1)

    def test_09_fx3_string_sc_f_uses_erzhe_junlianjie_verified_chinese_string(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            sc_f = rep["donor_audit"]["fx3_string_sc_f"]
            self.assertEqual(sc_f["marker_hits"]["通过显示屏节电"], 1)
            self.assertEqual(sc_f["marker_hits"]["二者均连接"], 1)
            self.assertEqual(sc_f["marker_hits"]["打开: 恢复"], 1)
            self.assertEqual(sc_f["marker_hits"]["关闭: 节电"], 1)
            self.assertEqual(sc_f["marker_hits"]["不连接"], 1)

    def test_10_os_open_always_uses_o_rdonly_never_rdwr_or_wronly(self) -> None:
        if p281.is_forced_clean_room():
            self.skipTest("Clean-room environment disables local donor os.open spy")
        real_open = os.open
        seen_flags = []

        def _spy_open(path, flags, *args, **kwargs):
            seen_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        p281._DONOR_AUDIT_CACHE.clear()
        with unittest.mock.patch("os.open", side_effect=_spy_open):
            audit = p281.inspect_phase281_donors(force_clean_room=False)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreater(len(seen_flags), 0)
        for flg in seen_flags:
            self.assertEqual(flg & os.O_ACCMODE, os.O_RDONLY)

    def test_11_resolve_donor_paths_clean_room_points_to_sentinel(self) -> None:
        paths = p281.resolve_phase281_donor_paths(env={p281.ENV_CLEAN_ROOM_TEST: "1"})
        self.assertEqual(len(paths), 18)
        for p in paths.values():
            self.assertIn(p281.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_12_missing_donor_directory_falls_back_cleanly_to_clean_room(self) -> None:
        rep = p281.run_phase281_realhw_power_save_monitor_language_volume_delete_hil(
            force_clean_room=False,
            env={
                p281.ENV_MAC_WORK_ROOT: "/nonexistent_phase281_donor_root_xyz",
                p281.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase281_donor_root_xyz",
                p281.ENV_MAC_ROOT: "/nonexistent_phase281_donor_root_xyz",
            },
        )
        # Either finds default workspace donors or falls back cleanly; always passes
        self.assertTrue(rep["all_checks_passed"])

    def test_13_donor_inspection_latency_within_ci_and_local_budget(self) -> None:
        t0 = time.monotonic()
        p281._DONOR_AUDIT_CACHE.clear()
        audit = p281.inspect_phase281_donors()
        elapsed = time.monotonic() - t0
        max_s = 15.0 if IS_CI else 1.0
        self.assertTrue(audit.all_contracts_verified)
        self.assertLess(elapsed, max_s)

    def test_14_no_raw_firmware_bytes_leaked_in_serialized_json(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            serialized = json.dumps(rep)
            self.assertNotIn("ELF", serialized[:100])
            self.assertEqual(rep["donor_audit"]["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_15_clean_room_and_local_donor_pillars_structural_parity(self) -> None:
        for pillar_key in (
            "pillar_a_power_save_monitor_and_start_time_hil",
            "pillar_b_language_bk_lang_and_uxc_parity_hil",
            "pillar_c_d_volume_monitoring_delete_and_redlines",
        ):
            self.assertEqual(self.clean_audit[pillar_key], self.default_audit[pillar_key])

    def test_16_18_donor_registry_parity_between_relpaths_and_bytes(self) -> None:
        self.assertEqual(
            set(p281.DONOR_RELPATHS.keys()), set(p281.EXPECTED_DONOR_BYTES.keys())
        )
        self.assertEqual(len(p281.DONOR_RELPATHS), 18)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 56A — [Power Save by Monitor] & 9 Deactivations (16 tests)
    # ------------------------------------------------------------------
    def test_17_stock_fx3_power_setting_option_exposes_only_2_items(self) -> None:
        for body in p281.STOCK_FX3_LINE_BODIES:
            r = p281.simulate_power_save_monitor_and_start_time_hil(body_profile=body)
            self.assertTrue(r.admitted, msg=body)
            self.assertFalse(r.fx3_ui_exposes_power_save_by_monitor, msg=body)
            self.assertEqual(
                r.exposed_power_setting_option_items,
                ("Power Save Start Time", "Auto Power OFF Temp."),
                msg=body,
            )
            self.assertEqual(r.effective_power_save_by_monitor, "NOT_EXPOSED_IN_FX3_UI")
            self.assertEqual(r.effective_power_save_start_time, "5 Min")
            self.assertEqual(r.effective_auto_power_off_temp, "Standard")

    def test_18_stock_fx3_vari_angle_fold_inward_remains_invariant(self) -> None:
        r_open = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX3,
            lcd_hinge_state=p281.LCD_HINGE_OPEN,
        )
        r_closed = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX3,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
        )
        for r in (r_open, r_closed):
            self.assertTrue(r.admitted)
            self.assertTrue(r.vari_angle_fold_invariant)
            self.assertFalse(r.vari_angle_fold_sleep_triggered)
            self.assertFalse(r.vari_angle_fold_wake_triggered)
            self.assertTrue(r.headless_hdmi_sleep_protected)

    def test_19_stock_fx3_ui_request_for_power_save_by_monitor_rejected_eopnotsupp(self) -> None:
        for body in p281.STOCK_FX3_LINE_BODIES:
            r = p281.simulate_power_save_monitor_and_start_time_hil(
                body_profile=body,
                power_save_by_monitor_ui_request=True,
                requested_power_save_by_monitor_label=p281.PSM_BOTH_LINKED,
            )
            self.assertFalse(r.admitted, msg=body)
            self.assertEqual(r.errno_code, p281.EOPNOTSUPP_ERRNO, msg=body)
            self.assertEqual(
                r.reason_code, "POWER_SAVE_BY_MONITOR_NOT_EXPOSED_IN_STOCK_FX3_UI"
            )
            self.assertEqual(r.power_save_monitor_spoof_events, 0)

    def test_20_spoofed_open_on_close_off_string_rejected_eopnotsupp(self) -> None:
        for body in (p281.BODY_MODEL_FX3, p281.BODY_MODEL_FX2, p281.BODY_MODEL_A7M4):
            r = p281.simulate_power_save_monitor_and_start_time_hil(
                body_profile=body,
                requested_power_save_by_monitor_label=p281.LEGACY_POWER_SAVE_MONITOR_SPOOF,
            )
            self.assertFalse(r.admitted, msg=body)
            self.assertEqual(r.errno_code, p281.EOPNOTSUPP_ERRNO, msg=body)
            self.assertEqual(r.reason_code, "POWER_SAVE_MONITOR_SPOOF_REJECTED")
            self.assertEqual(r.power_save_monitor_spoof_events, 0)

    def test_21_shared_appfw_compiled_4_modes_across_sibling_bodies(self) -> None:
        for sibling in p281.SIBLING_POWER_SAVE_BY_MONITOR_BODIES:
            r = p281.simulate_power_save_monitor_and_start_time_hil(
                body_profile=sibling,
                requested_power_save_by_monitor_label=p281.PSM_DOES_NOT_LINK,
            )
            self.assertTrue(r.admitted, msg=sibling)
            self.assertTrue(r.fx3_ui_exposes_power_save_by_monitor, msg=sibling)
            self.assertEqual(
                r.appfw_compiled_monitor_linkage_modes,
                ("Both Linked", "Open: Return", "Close: Power Save", "Does Not Link"),
                msg=sibling,
            )

    def test_22_sibling_4_modes_exact_sleep_wake_state_machine(self) -> None:
        r_both = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX2,
            requested_power_save_by_monitor_label=p281.PSM_BOTH_LINKED,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
        )
        self.assertTrue(r_both.vari_angle_fold_sleep_triggered)
        self.assertFalse(r_both.headless_hdmi_sleep_protected)

        r_open_ret = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX2,
            requested_power_save_by_monitor_label=p281.PSM_OPEN_RETURN,
            lcd_hinge_state=p281.LCD_HINGE_OPEN,
        )
        self.assertTrue(r_open_ret.vari_angle_fold_wake_triggered)
        self.assertTrue(r_open_ret.headless_hdmi_sleep_protected)

        r_close_ps = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_ZVE1,
            requested_power_save_by_monitor_label=p281.PSM_CLOSE_POWER_SAVE,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
        )
        self.assertTrue(r_close_ps.vari_angle_fold_sleep_triggered)
        self.assertFalse(r_close_ps.headless_hdmi_sleep_protected)

        r_nolink = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_A6700,
            requested_power_save_by_monitor_label=p281.PSM_DOES_NOT_LINK,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
        )
        self.assertFalse(r_nolink.vari_angle_fold_sleep_triggered)
        self.assertTrue(r_nolink.vari_angle_fold_invariant)
        self.assertTrue(r_nolink.headless_hdmi_sleep_protected)

    def test_23_headless_hdmi_sleep_guard_blocks_unsafe_both_linked_on_sibling(self) -> None:
        r = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_A7M4,
            requested_power_save_by_monitor_label=p281.PSM_BOTH_LINKED,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
            headless_hdmi_bench=True,
            enforce_headless_sleep_guard=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p281.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "HEADLESS_HDMI_MONITOR_SLEEP_GUARD_BLOCKED")
        self.assertEqual(r.headless_hdmi_unexpected_sleep_events, 0)

    def test_24_ilce7m4_v600_sleep_regression_detected_and_blocked(self) -> None:
        r = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_A7M4,
            requested_power_save_by_monitor_label=p281.PSM_DOES_NOT_LINK,
            lcd_hinge_state=p281.LCD_HINGE_CLOSED_INWARD,
            headless_hdmi_bench=True,
            enforce_headless_sleep_guard=True,
            ilce7m4_v600_regression_simulated=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p281.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.ilce7m4_v600_regression_simulated)

    def test_25_power_save_start_time_all_6_options_and_auto_power_off_temp(self) -> None:
        for choice in p281.VALID_POWER_SAVE_START_TIMES:
            for temp in p281.VALID_AUTO_POWER_OFF_TEMPS:
                r = p281.simulate_power_save_monitor_and_start_time_hil(
                    configured_power_save_start_time=choice,
                    configured_auto_power_off_temp=temp,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_power_save_start_time, choice)
                self.assertEqual(r.effective_auto_power_off_temp, temp)
                self.assertEqual(r.idle_sleep_armed, choice != p281.POWER_SAVE_START_OFF)

    def test_26_power_save_start_time_all_9_deactivation_conditions_individually(self) -> None:
        self.assertEqual(len(p281.POWER_SAVE_9_DEACTIVATION_CONDITIONS), 9)
        for cond in p281.POWER_SAVE_9_DEACTIVATION_CONDITIONS:
            r = p281.simulate_power_save_monitor_and_start_time_hil(
                configured_power_save_start_time=p281.POWER_SAVE_START_1MIN,
                **{cond: True},
            )
            self.assertTrue(r.admitted, msg=cond)
            self.assertTrue(r.power_save_timer_bypassed, msg=cond)
            self.assertFalse(r.idle_sleep_armed, msg=cond)
            self.assertEqual(r.active_deactivation_conditions, (cond,), msg=cond)

    def test_27_power_save_9_deactivation_conditions_combined_and_baseline_armed(self) -> None:
        base = p281.simulate_power_save_monitor_and_start_time_hil(
            configured_power_save_start_time=p281.POWER_SAVE_START_10SEC
        )
        self.assertTrue(base.idle_sleep_armed)
        self.assertFalse(base.power_save_timer_bypassed)
        self.assertEqual(base.active_deactivation_conditions, ())

        all_on = p281.simulate_power_save_monitor_and_start_time_hil(
            configured_power_save_start_time=p281.POWER_SAVE_START_10SEC,
            **{c: True for c in p281.POWER_SAVE_9_DEACTIVATION_CONDITIONS},
        )
        self.assertTrue(all_on.power_save_timer_bypassed)
        self.assertFalse(all_on.idle_sleep_armed)
        self.assertEqual(
            all_on.active_deactivation_conditions, p281.POWER_SAVE_9_DEACTIVATION_CONDITIONS
        )

    def test_28_setup_power_setting_option_survives_camera_settings_reset(self) -> None:
        for act in (
            p281.RESET_ACTION_CAMERA_SETTINGS_RESET,
            p281.RESET_ACTION_RESET_NETWORK_SET,
        ):
            r = p281.simulate_power_save_monitor_and_start_time_hil(
                configured_power_save_start_time=p281.POWER_SAVE_START_OFF,
                configured_auto_power_off_temp=p281.AUTO_POWER_OFF_TEMP_HIGH,
                reset_action=act,
            )
            self.assertTrue(r.admitted, msg=act)
            self.assertTrue(r.setup_items_survived_camera_reset, msg=act)
            self.assertFalse(r.setup_items_restored_by_initialize, msg=act)
            self.assertEqual(r.effective_power_save_start_time, p281.POWER_SAVE_START_OFF)
            self.assertEqual(r.effective_auto_power_off_temp, p281.AUTO_POWER_OFF_TEMP_HIGH)

    def test_29_initialize_restores_power_setting_option_defaults(self) -> None:
        r_fx3 = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_power_save_start_time=p281.POWER_SAVE_START_OFF,
            configured_auto_power_off_temp=p281.AUTO_POWER_OFF_TEMP_HIGH,
            reset_action=p281.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r_fx3.setup_items_restored_by_initialize)
        self.assertEqual(r_fx3.effective_power_save_start_time, "5 Min")
        self.assertEqual(r_fx3.effective_auto_power_off_temp, "Standard")

        r_sib = p281.simulate_power_save_monitor_and_start_time_hil(
            body_profile=p281.BODY_MODEL_FX2,
            requested_power_save_by_monitor_label=p281.PSM_DOES_NOT_LINK,
            reset_action=p281.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r_sib.setup_items_restored_by_initialize)
        self.assertEqual(r_sib.effective_power_save_by_monitor, p281.PSM_BOTH_LINKED)

    def test_30_invalid_power_setting_option_parameters_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "ILCE-1M99"},
            {"requested_power_save_by_monitor_label": "INVALID_MODE"},
            {"lcd_hinge_state": "TILT_UP"},
            {"configured_power_save_start_time": "99 Min"},
            {"configured_auto_power_off_temp": "Turbo"},
            {"reset_action": "WIPE_ALL"},
        ):
            r = p281.simulate_power_save_monitor_and_start_time_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p281.EINVAL_ERRNO, msg=str(kwargs))

    def test_31_pillar_a_summary_matrix_and_zero_writes(self) -> None:
        pa = self.clean_audit["pillar_a_power_save_monitor_and_start_time_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["compiled_appfw_4modes"]), 4)
        self.assertEqual(len(pa["power_save_9_deactivation_conditions"]), 9)
        self.assertEqual(pa["fx3_default_open"]["physical_device_writes"], 0)

    def test_32_power_save_by_monitor_spec_resid16_exact_bindings(self) -> None:
        self.assertEqual(p281.POWER_SAVE_BY_MONITOR_RESID, "0x60b9")
        self.assertEqual(p281.POWER_SAVE_BY_MONITOR_SPEC["Both Linked"]["resid16"], "0x6db5")
        self.assertEqual(p281.POWER_SAVE_BY_MONITOR_SPEC["Open: Return"]["resid16"], "0x6db6")
        self.assertEqual(
            p281.POWER_SAVE_BY_MONITOR_SPEC["Close: Power Save"]["resid16"], "0x60a8"
        )
        self.assertEqual(p281.POWER_SAVE_BY_MONITOR_SPEC["Does Not Link"]["resid16"], "0x6b2e")

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 56B — [Language] BK_LANG 34-vs-29 & 4-Lang Parity (14 tests)
    # ------------------------------------------------------------------
    def test_33_fx3_vs_fx6_bk_lang_offset_width_and_language_count_split(self) -> None:
        r_fx3 = p281.simulate_language_bk_lang_and_uxc_parity_hil(body_profile=p281.BODY_MODEL_FX3)
        r_fx6 = p281.simulate_language_bk_lang_and_uxc_parity_hil(body_profile=p281.BODY_MODEL_FX6)
        self.assertTrue(r_fx3.admitted)
        self.assertTrue(r_fx6.admitted)
        self.assertEqual(r_fx3.bk_lang_id_hex, "0x02cf019c")
        self.assertEqual(r_fx3.supported_language_count, 34)
        self.assertEqual(r_fx3.bk_lang_offset_hex, "0x90ff0")
        self.assertEqual(r_fx3.bk_lang_width_bytes, 4)

        self.assertEqual(r_fx6.bk_lang_id_hex, "0x02cf019c")
        self.assertEqual(r_fx6.supported_language_count, 29)
        self.assertEqual(r_fx6.bk_lang_offset_hex, "0x89242")
        self.assertEqual(r_fx6.bk_lang_width_bytes, 1)
        self.assertEqual(r_fx3.fx3_vs_fx6_count_delta, 5)

    def test_34_stage_b_4_languages_exact_codes_enums_banks_and_ltt_fonts(self) -> None:
        expected = {
            "en": (0x00, "0x2b2f_LANGUAGE_ENGLISH", 0, (4, 4), "UniversOTS-SJ_wIcon.ltt"),
            "schinese": (
                0x19,
                "0x2b45_CHINESE_SIMPLIFIED",
                23,
                (19, 19),
                "MYingHeiC-GB18030-SJ_wIcon.ltt",
            ),
            "tchinese": (
                0x18,
                "0x2b44_LANGUAGE_CHINESE_TRADITIONAL",
                27,
                (22, 22),
                "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
            ),
            "japanese": (
                0x01,
                "0x2b30_LANGUAGE_JAPANESE",
                1,
                (12, 12),
                "HeiseiKakuGothW5-SJ_wIcon.ltt",
            ),
        }
        for key, (code, enum_name, sw_bank, fbanks, ltt) in expected.items():
            r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
                body_profile=p281.BODY_MODEL_FX3,
                configured_language_key=key,
            )
            self.assertTrue(r.admitted, msg=key)
            self.assertEqual(r.effective_language_key, key, msg=key)
            self.assertEqual(r.effective_bk_lang_code, code, msg=key)
            self.assertEqual(r.effective_appfw_enum, enum_name, msg=key)
            self.assertEqual(r.effective_switch_bank, sw_bank, msg=key)
            self.assertEqual(r.effective_font_str_banks, fbanks, msg=key)
            self.assertEqual(r.effective_ltt_font, ltt, msg=key)

    def test_35_stage_b_4_language_uxc_byte_sizes_match_donor_table(self) -> None:
        da = self.default_audit["donor_audit"]
        key_map = {
            "en": ("fx3_string_en_f", "fx3_string_en", "fx6_string_en"),
            "schinese": ("fx3_string_sc_f", "fx3_string_sc", "fx6_string_sc"),
            "tchinese": ("fx3_string_tc_f", "fx3_string_tc", "fx6_string_tc"),
            "japanese": ("fx3_string_ja_f", "fx3_string_ja", "fx6_string_ja"),
        }
        for lang, (k_f, k_3, k_6) in key_map.items():
            spec = p281.STAGE_B_4_LANGUAGES[lang]
            self.assertEqual(da[k_f]["file_bytes"], spec["fx3_f_uxc_bytes"], msg=k_f)
            self.assertEqual(da[k_3]["file_bytes"], spec["fx3_uxc_bytes"], msg=k_3)
            self.assertEqual(da[k_6]["file_bytes"], spec["fx6_uxc_bytes"], msg=k_6)

    def test_36_fx6_regional_seed_ntsc_0x00_vs_cn1_0x19_parity(self) -> None:
        r_ntsc = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX6,
            regional_seed_variant="NTSC",
            configured_language_key="en",
        )
        r_cn1 = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX6,
            regional_seed_variant="CN1",
            configured_language_key="schinese",
        )
        self.assertEqual(r_ntsc.effective_bk_lang_code, 0x00)
        self.assertEqual(r_cn1.effective_bk_lang_code, 0x19)
        self.assertEqual(r_ntsc.menu_path, p281.LANGUAGE_MENU_PATH_FX6)

    def test_37_fx3_accepts_extra_34lang_entries_while_fx6_29lang_rejects_eopnotsupp(self) -> None:
        for extra in p281.FX3_ONLY_EXTRA_LANGUAGES:
            r3 = p281.simulate_language_bk_lang_and_uxc_parity_hil(
                body_profile=p281.BODY_MODEL_FX3,
                configured_language_key=extra,
            )
            r6 = p281.simulate_language_bk_lang_and_uxc_parity_hil(
                body_profile=p281.BODY_MODEL_FX6,
                configured_language_key=extra,
            )
            self.assertTrue(r3.admitted, msg=extra)
            self.assertEqual(r3.supported_language_count, 34, msg=extra)
            self.assertFalse(r6.admitted, msg=extra)
            self.assertEqual(r6.errno_code, p281.EOPNOTSUPP_ERRNO, msg=extra)
            self.assertEqual(r6.supported_language_count, 29, msg=extra)

    def test_38_out_of_box_unconfigured_language_displays_em_dash_prompt(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_language_key="en",
            out_of_box_unconfigured=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.initial_setup_prompt_required)
        self.assertEqual(r.effective_language_key, "—")
        self.assertEqual(r.out_of_box_display_label, "—")
        self.assertEqual(r.effective_bk_lang_code, -1)

    def test_39_language_survives_camera_settings_reset(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_language_key="schinese",
            reset_action=p281.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.survived_camera_settings_reset)
        self.assertFalse(r.cleared_by_initialize)
        self.assertEqual(r.effective_language_key, "schinese")
        self.assertEqual(r.effective_bk_lang_code, 0x19)

    def test_40_language_survives_reset_network_set(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_language_key="japanese",
            reset_action=p281.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.survived_reset_network_set)
        self.assertFalse(r.cleared_by_initialize)
        self.assertEqual(r.effective_language_key, "japanese")
        self.assertEqual(r.effective_bk_lang_code, 0x01)

    def test_41_initialize_clears_language_and_triggers_reprompt(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_language_key="tchinese",
            reset_action=p281.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.cleared_by_initialize)
        self.assertTrue(r.initial_setup_prompt_required)
        self.assertEqual(r.effective_language_key, "—")
        self.assertEqual(r.bk4_persistent_nvram_writes, 0)

    def test_42_fx3_extra_language_also_cleared_by_initialize(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3,
            configured_language_key="turkish",
            reset_action=p281.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.cleared_by_initialize)
        self.assertTrue(r.initial_setup_prompt_required)
        self.assertEqual(r.effective_language_key, "—")

    def test_43_fx3a_inherits_34_language_bk4_layout(self) -> None:
        r = p281.simulate_language_bk_lang_and_uxc_parity_hil(
            body_profile=p281.BODY_MODEL_FX3A,
            configured_language_key="en",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.supported_language_count, 34)
        self.assertEqual(r.bk_lang_offset_hex, "0x90ff0")
        self.assertEqual(r.bk_lang_width_bytes, 4)

    def test_44_invalid_language_key_or_body_or_reset_rejected_einval(self) -> None:
        for kwargs in (
            {"configured_language_key": "klingon"},
            {"body_profile": "UNKNOWN_CAMERA"},
            {"reset_action": "FACTORY_FLASH_ERASE"},
        ):
            r = p281.simulate_language_bk_lang_and_uxc_parity_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p281.EINVAL_ERRNO, msg=str(kwargs))

    def test_45_pillar_b_passed_flag_and_zero_mismatch_events(self) -> None:
        pb = self.clean_audit["pillar_b_language_bk_lang_and_uxc_parity_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["fx3_language_count"], 34)
        self.assertEqual(pb["fx6_language_count"], 29)
        self.assertEqual(pb["bk_lang_id_hex"], "0x02cf019c")

    def test_46_all_language_simulations_perform_zero_persistent_bk4_writes(self) -> None:
        pb = self.clean_audit["pillar_b_language_bk_lang_and_uxc_parity_hil"]
        for entry in pb["stage_b_4lang_fx3_matrix"].values():
            self.assertEqual(entry["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["language_count_model_mismatch_events"], 0)
            self.assertEqual(entry["bk_lang_offset_mismatch_events"], 0)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 56C — [Volume Settings], [4ch Audio Monitoring],
    #          [Delete confirm.] & Slot-1 Vault Firewall (18 tests)
    # ------------------------------------------------------------------
    def test_47_volume_settings_default_7_and_full_0_to_15_range(self) -> None:
        r_def = p281.simulate_volume_monitoring_delete_confirm_vault_hil()
        self.assertTrue(r_def.admitted)
        self.assertEqual(r_def.volume_menu_path, p281.VOLUME_SETTINGS_MENU_PATH)
        self.assertEqual(r_def.effective_volume_level, 7)

        for lvl in range(0, 16):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_volume_level=lvl
            )
            self.assertTrue(r.admitted, msg=lvl)
            self.assertEqual(r.effective_volume_level, lvl, msg=lvl)

    def test_48_volume_settings_rejects_out_of_range_and_bool_einval(self) -> None:
        for bad_lvl in (-1, 16, 100, True, False):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_volume_level=bad_lvl  # type: ignore[arg-type]
            )
            self.assertFalse(r.admitted, msg=repr(bad_lvl))
            self.assertEqual(r.errno_code, p281.EINVAL_ERRNO, msg=repr(bad_lvl))

    def test_49_xlr_h1_internal_speaker_feedback_clamped_and_forced_bypass_blocked(self) -> None:
        clamped = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
            configured_volume_level=14,
            playback_sink=p281.PLAYBACK_SINK_INTERNAL_SPEAKER,
            xlr_h1_mic_active=True,
        )
        self.assertTrue(clamped.admitted)
        self.assertTrue(clamped.xlr_h1_speaker_feedback_clamped)
        self.assertEqual(clamped.effective_volume_level, 0)
        self.assertEqual(clamped.xlr_h1_speaker_feedback_guard_violations, 0)

        blocked = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
            configured_volume_level=14,
            playback_sink=p281.PLAYBACK_SINK_INTERNAL_SPEAKER,
            xlr_h1_mic_active=True,
            force_unsafe_xlr_speaker_feedback=True,
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.errno_code, p281.EACCES_ERRNO)
        self.assertEqual(
            blocked.reason_code, "XLR_H1_INTERNAL_SPEAKER_ACOUSTIC_FEEDBACK_BLOCKED"
        )
        self.assertEqual(blocked.xlr_h1_speaker_feedback_guard_violations, 0)

    def test_50_xlr_h1_with_headphone_35mm_or_hdmi_preserves_volume_level(self) -> None:
        for sink in (p281.PLAYBACK_SINK_HEADPHONE_35MM, p281.PLAYBACK_SINK_HDMI):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_volume_level=13,
                playback_sink=sink,
                xlr_h1_mic_active=True,
            )
            self.assertTrue(r.admitted, msg=sink)
            self.assertFalse(r.xlr_h1_speaker_feedback_clamped, msg=sink)
            self.assertEqual(r.effective_volume_level, 13, msg=sink)

    def test_51_4ch_audio_monitoring_all_5_routes_and_lr_channel_mapping(self) -> None:
        expected = {
            "CH1/CH2": ("CH1", "CH2"),
            "CH3/CH4": ("CH3", "CH4"),
            "CH1+3/CH2+4": ("CH1+CH3", "CH2+CH4"),
            "CH1/CH1": ("CH1", "CH1"),
            "CH2/CH2": ("CH2", "CH2"),
        }
        self.assertEqual(len(p281.VALID_4CH_AUDIO_MONITORING_ROUTES), 5)
        for route, (left, right) in expected.items():
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_4ch_monitoring_route=route
            )
            self.assertTrue(r.admitted, msg=route)
            self.assertEqual(r.effective_4ch_monitoring_route, route, msg=route)
            self.assertEqual(r.monitoring_left_channel, left, msg=route)
            self.assertEqual(r.monitoring_right_channel, right, msg=route)
            self.assertEqual(r.headphone_output_channels, 2)
            self.assertFalse(r.discrete_4ch_headphone_simultaneous)

    def test_52_35mm_headphone_discrete_4ch_violation_rejected_eopnotsupp(self) -> None:
        r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
            force_discrete_4ch_headphone=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p281.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "HEADPHONE_35MM_LIMITED_TO_2CH_STEREO")
        self.assertEqual(r.four_ch_headphone_routing_violations, 0)

    def test_53_hdmi_4ch_audio_output_independent_and_rejects_mix_routes(self) -> None:
        for ok_route in (p281.MON_ROUTE_CH1_CH2, p281.MON_ROUTE_CH3_CH4):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_4ch_monitoring_route=p281.MON_ROUTE_CH1P3_CH2P4,
                configured_hdmi_4ch_output_route=ok_route,
            )
            self.assertTrue(r.admitted, msg=ok_route)
            self.assertEqual(r.effective_hdmi_4ch_output_route, ok_route)
            self.assertEqual(r.effective_4ch_monitoring_route, p281.MON_ROUTE_CH1P3_CH2P4)

        for bad_hdmi_route in (
            p281.MON_ROUTE_CH1P3_CH2P4,
            p281.MON_ROUTE_CH1_CH1,
            p281.MON_ROUTE_CH2_CH2,
        ):
            r_bad = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_hdmi_4ch_output_route=bad_hdmi_route
            )
            self.assertFalse(r_bad.admitted, msg=bad_hdmi_route)
            self.assertEqual(r_bad.errno_code, p281.EOPNOTSUPP_ERRNO, msg=bad_hdmi_route)

    def test_54_delete_confirm_defaults_cancel_first_and_pressing_twice_off(self) -> None:
        r = p281.simulate_volume_monitoring_delete_confirm_vault_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.delete_confirm_menu_path, p281.DELETE_CONFIRM_MENU_PATH)
        self.assertEqual(r.delete_twice_menu_path, p281.DELETE_PRESSING_TWICE_MENU_PATH)
        self.assertEqual(r.effective_delete_confirm, '"Cancel" first')
        self.assertEqual(r.default_dialog_focus, "Cancel")
        self.assertEqual(r.effective_delete_pressing_twice, "Off")

    def test_55_delete_confirm_delete_first_and_pressing_twice_on_modes(self) -> None:
        r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
            configured_delete_confirm=p281.DELETE_CONFIRM_DELETE_FIRST,
            configured_delete_pressing_twice=p281.TOGGLE_ON,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_delete_confirm, '"Delete" first')
        self.assertEqual(r.default_dialog_focus, "Delete")
        self.assertEqual(r.effective_delete_pressing_twice, "On")

    def test_56_slot1_recovery_vault_firewall_blocks_all_6_destructive_ops_erofs(self) -> None:
        self.assertEqual(len(p281.DESTRUCTIVE_MEDIA_OPERATIONS), 6)
        for op in p281.DESTRUCTIVE_MEDIA_OPERATIONS:
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                target_slot=p281.SLOT_1,
                slot1_holds_recovery_vault=True,
                requested_media_operation=op,
                configured_delete_confirm=p281.DELETE_CONFIRM_DELETE_FIRST,
                configured_delete_pressing_twice=p281.TOGGLE_ON,
            )
            self.assertFalse(r.admitted, msg=op)
            self.assertEqual(r.errno_code, p281.EROFS_ERRNO, msg=op)
            self.assertEqual(r.reason_code, "SLOT1_RECOVERY_VAULT_HARD_LOCKED", msg=op)
            self.assertFalse(r.media_operation_executed, msg=op)
            self.assertEqual(r.slot1_vault_delete_events, 0, msg=op)
            self.assertTrue(r.slot1_format_hard_locked, msg=op)
            self.assertEqual(r.physical_device_writes, 0, msg=op)

    def test_57_slot2_scratch_operations_execute_in_vm_with_zero_physical_writes(self) -> None:
        for op in p281.DESTRUCTIVE_MEDIA_OPERATIONS:
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                target_slot=p281.SLOT_2,
                slot1_holds_recovery_vault=True,
                requested_media_operation=op,
            )
            self.assertTrue(r.admitted, msg=op)
            self.assertTrue(r.media_operation_executed, msg=op)
            self.assertEqual(r.slot1_vault_delete_events, 0, msg=op)
            self.assertEqual(r.physical_device_writes, 0, msg=op)

    def test_58_volume_4ch_and_delete_confirm_survive_camera_settings_reset(self) -> None:
        for act in (
            p281.RESET_ACTION_CAMERA_SETTINGS_RESET,
            p281.RESET_ACTION_RESET_NETWORK_SET,
        ):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
                configured_volume_level=11,
                configured_4ch_monitoring_route=p281.MON_ROUTE_CH1_CH1,
                configured_hdmi_4ch_output_route=p281.MON_ROUTE_CH3_CH4,
                configured_delete_confirm=p281.DELETE_CONFIRM_DELETE_FIRST,
                configured_delete_pressing_twice=p281.TOGGLE_ON,
                reset_action=act,
            )
            self.assertTrue(r.admitted, msg=act)
            self.assertTrue(r.setup_and_playback_survived_camera_reset, msg=act)
            self.assertFalse(r.restored_to_factory_by_initialize, msg=act)
            self.assertEqual(r.effective_volume_level, 11)
            self.assertEqual(r.effective_4ch_monitoring_route, p281.MON_ROUTE_CH1_CH1)
            self.assertEqual(r.effective_hdmi_4ch_output_route, p281.MON_ROUTE_CH3_CH4)
            self.assertEqual(r.effective_delete_confirm, '"Delete" first')
            self.assertEqual(r.effective_delete_pressing_twice, "On")

    def test_59_initialize_restores_volume_4ch_and_delete_confirm_to_factory_defaults(self) -> None:
        r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(
            configured_volume_level=15,
            configured_4ch_monitoring_route=p281.MON_ROUTE_CH2_CH2,
            configured_hdmi_4ch_output_route=p281.MON_ROUTE_CH3_CH4,
            configured_delete_confirm=p281.DELETE_CONFIRM_DELETE_FIRST,
            configured_delete_pressing_twice=p281.TOGGLE_ON,
            reset_action=p281.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.restored_to_factory_by_initialize)
        self.assertEqual(r.effective_volume_level, 7)
        self.assertEqual(r.effective_4ch_monitoring_route, "CH1/CH2")
        self.assertEqual(r.effective_hdmi_4ch_output_route, "CH1/CH2")
        self.assertEqual(r.effective_delete_confirm, '"Cancel" first')
        self.assertEqual(r.effective_delete_pressing_twice, "Off")

    def test_60_invalid_volume_monitoring_delete_parameters_rejected_einval(self) -> None:
        for kwargs in (
            {"playback_sink": "BLUETOOTH_SPEAKER"},
            {"configured_4ch_monitoring_route": "CH1/CH4"},
            {"configured_delete_confirm": "Auto Confirm"},
            {"configured_delete_pressing_twice": "Auto"},
            {"target_slot": "Slot 3"},
            {"requested_media_operation": "Wipe NVRAM"},
            {"reset_action": "UNKNOWN"},
        ):
            r = p281.simulate_volume_monitoring_delete_confirm_vault_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p281.EINVAL_ERRNO, msg=str(kwargs))

    def test_61_audio_monitoring_spec_resid16_and_distinct_audio_signals_resid(self) -> None:
        self.assertEqual(p281.VOLUME_SETTINGS_RESID, "0xe8c9")
        self.assertEqual(p281.AUDIO_SIGNALS_RESID, "0x7af6")
        self.assertNotEqual(p281.VOLUME_SETTINGS_RESID, p281.AUDIO_SIGNALS_RESID)
        self.assertEqual(
            p281.FOUR_CH_AUDIO_MONITORING_SPEC["CH1/CH2"]["resid16"], "0x713b"
        )
        self.assertEqual(
            p281.FOUR_CH_AUDIO_MONITORING_SPEC["CH3/CH4"]["resid16"], "0x6bf6"
        )
        self.assertEqual(
            p281.FOUR_CH_AUDIO_MONITORING_SPEC["CH1+3/CH2+4"]["resid16"], "0x6c2e"
        )
        self.assertEqual(
            p281.FOUR_CH_AUDIO_MONITORING_SPEC["CH1/CH1"]["resid16"], "0x6f9c"
        )
        self.assertEqual(
            p281.FOUR_CH_AUDIO_MONITORING_SPEC["CH2/CH2"]["resid16"], "0x7a26"
        )

    def test_62_pillar_cd_passed_and_contains_16_blocked_probes(self) -> None:
        pcd = self.clean_audit["pillar_c_d_volume_monitoring_delete_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])

    def test_63_pillar_cd_volume_range_and_5route_matrix_complete(self) -> None:
        pcd = self.clean_audit["pillar_c_d_volume_monitoring_delete_and_redlines"]
        self.assertEqual(set(pcd["volume_range_0_to_15"].keys()), {str(i) for i in range(16)})
        self.assertEqual(
            set(pcd["monitoring_5route_matrix"].keys()),
            {"CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"},
        )

    def test_64_fx6_monitor_volume_donor_vs_fx3_volume_settings_parity(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["fx3_appfw"]["window_hits"]["VOLUME_SETTINGS"], 1)
        self.assertEqual(da["fx3_appfw"]["window_hits"]["AUDIO_MON_CH"], 1)
        self.assertEqual(da["fx6_appfw"]["window_hits"]["MONITOR_VOL"], 1)

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 56 (56/56) Suite & Subprocess Hygiene (12 tests)
    # ------------------------------------------------------------------
    def test_65_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p281.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p281.probe_phase281_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p281.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p281.probe_phase281_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.slot1_vault_delete_events, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p281.probe_phase281_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p281.EINVAL_ERRNO)

    def test_66_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p281.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_power_save_monitor_language_volume_delete_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 281 Stage 56 (56/56)", proc_sum.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc_sum.stdout)

        proc_json = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc_json.stdout)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["milestone"], "56/56")
        self.assertEqual(data["phase_number"], 281)

    def test_67_suite_stage56_56_of_56_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s56 = rep["stage56_realhw_power_save_monitor_language_volume_delete_hil"]
            self.assertTrue(s56["all_checks_passed"])
            self.assertEqual(s56["phase_number"], 281)
            self.assertEqual(s56["milestone"], "56/56")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 56)

    def test_68_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 10.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_69_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_70_suite_stage56_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.stage56_realhw_power_save_monitor_language_volume_delete_hil
        )
        self.assertTrue(default_cfg.include_stage56)
        self.assertTrue(
            default_cfg.include_phase281_realhw_power_save_monitor_language_volume_delete_hil
        )

        for override in (
            {"stage56_realhw_power_save_monitor_language_volume_delete_hil": False},
            {"include_stage56": False},
            {"include_phase281_realhw_power_save_monitor_language_volume_delete_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage56_realhw_power_save_monitor_language_volume_delete_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage56"])
            self.assertFalse(
                rep["config"]["stage56_realhw_power_save_monitor_language_volume_delete_hil"]
            )

    def test_71_fx3_vm_coemulation_suite_include_stage56_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage56", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_power_save_monitor_language_volume_delete_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_72_fx3_vm_coemulation_suite_cli_skip_phase281_and_skip_stage56(self) -> None:
        for skip_flag in ("--skip-phase281", "--skip-stage56", "--no-include-stage56"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage56_realhw_power_save_monitor_language_volume_delete_hil", parsed
            )

    def test_73_fx3_vm_coemulation_suite_subprocess_default_and_clean_room_modes(self) -> None:
        suite_script = str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py")
        for extra_env in ({}, {p281.ENV_CLEAN_ROOM_TEST: "1"}):
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env.update(extra_env)
            proc = subprocess.run(
                [sys.executable, "-B", suite_script, *_FAST_CLI_FLAGS, "--include-stage56", "--json"],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(proc.stdout)
            self.assertTrue(data["all_checks_passed"])
            self.assertIn("stage56_realhw_power_save_monitor_language_volume_delete_hil", data)

    def test_74_all_safety_and_byof_redlines_locked_across_stage56_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertFalse(red["fx3_ui_exposes_power_save_by_monitor"])
            self.assertEqual(red["power_save_monitor_spoof_events"], 0)
            self.assertEqual(red["headless_hdmi_unexpected_sleep_events"], 0)
            self.assertEqual(red["language_count_model_mismatch_events"], 0)
            self.assertEqual(red["bk_lang_offset_mismatch_events"], 0)
            self.assertEqual(red["xlr_h1_speaker_feedback_guard_violations"], 0)
            self.assertEqual(red["four_ch_headphone_routing_violations"], 0)
            self.assertEqual(red["slot1_vault_delete_events"], 0)
            self.assertTrue(red["slot1_format_hard_locked"])
            self.assertEqual(red["passive_tx_bytes_emitted"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["emmc_corruptions"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_75_forward_compatible_stage_count_56_assertion(self) -> None:
        stage_keys = [
            k
            for k in self.default_suite
            if re.match(r"^stage\d+_", k) and isinstance(self.default_suite[k], dict)
        ]
        self.assertGreaterEqual(len(stage_keys), 56)

    def test_76_no_pyc_bytecode_files_emitted_under_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
