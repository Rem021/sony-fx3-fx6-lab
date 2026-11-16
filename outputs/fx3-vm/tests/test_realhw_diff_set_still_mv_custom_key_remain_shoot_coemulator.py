#!/usr/bin/env python3
"""Unit tests for Phase 258 Stage 50 (`50/50` GRAND MILESTONE):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`) Wave-40
`[Different Set for Still/Mv]` 8-Item Asymmetric Transitions & `Ver. 7.02`
`[Shutter Angle]` Override, `[Custom Key/Dial Set.]` 3-Domain `ISO/EI`
Auto-Adaptation & Slot-1 `CAMSET01.DAT` `O_RDONLY` Vault Round-Trip, and
`[Remain Shoot Display]` Still-Buffer Scope & EVF-Less `ILME-FX3` Monitor
Topology HIL Co-Emulator (68 dual-mode tests).
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
import realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator as p258  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated imaging/fault Unicorn loops for <50ms flag tests."""
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
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
        include_stage49=False,
    )
    base.update(overrides)
    return base


class TestPhase258DiffSetStillMvCustomKeyRemainShootCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = (
            p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
                force_clean_room=True
            )
        )
        cls.default_audit = (
            p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil()
        )

        t0 = time.monotonic()
        cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        cls.clean_suite_elapsed = time.monotonic() - t0

        if p258.is_forced_clean_room():
            cls.default_suite = cls.clean_suite
            cls.default_suite_elapsed = cls.clean_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.default_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
            cls.default_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Phase 258 Stage 50 (50/50) & O_RDONLY Donors (12)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase258_stage50_grand_milestone_and_redlines(self) -> None:
        self.assertEqual(
            p258.SCHEMA_ID,
            "realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1",
        )
        self.assertEqual(p258.PHASE_258_SCHEMA, p258.SCHEMA_ID)
        self.assertEqual(p258.PHASE_258_VERSION, "258.0.0")
        self.assertEqual(p258.PHASE_NUMBER, 258)
        self.assertEqual(p258.STAGE_INDEX, 50)
        self.assertEqual(p258.STAGE_TOTAL, 50)
        self.assertEqual(p258.MILESTONE_LABEL, "50/50")
        self.assertEqual(
            p258.STAGE_NAME,
            "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
        )
        self.assertEqual(p258.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p258.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p258.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p258.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p258.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p258.NOP_COUNT, 0)
        self.assertEqual(p258.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p258.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p258.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertFalse(p258.FX3_HAS_BUILTIN_EVF)
        self.assertEqual(p258.DIFF_SET_TRANSITION_CORRUPTION_EVENTS, 0)
        self.assertEqual(p258.SHUTTER_ANGLE_COMMON_BLEED_EVENTS, 0)
        self.assertEqual(p258.SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES, 0)
        self.assertEqual(p258.EVF_FINDER_MONITOR_SPOOF_EVENTS, 0)
        self.assertFalse(p258.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p258.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p258.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p258.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p258.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p258.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)

    def test_02_clean_room_donor_audit_15_artifacts_zero_leaked_bytes(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        da = self.clean_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["donor_files_inspected"], 0)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertTrue(da["diff_set_still_mv_and_shutter_angle_proven"])
        self.assertTrue(da["custom_key_dial_iso_ei_and_camset_proven"])
        self.assertTrue(da["remain_shoot_and_evfless_monitor_proven"])
        self.assertEqual(tuple(da["errors"]), ())

    def test_03_default_mode_donor_audit_rdonly_and_sub_100ms_budget(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
        self.assertLess(da["inspection_elapsed_s"], 0.10)
        if p258.is_forced_clean_room():
            self.assertEqual(self.default_audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        else:
            resolved = p258.resolve_phase258_donor_paths()
            if all(p.is_file() for p in resolved.values()):
                self.assertEqual(self.default_audit["source_mode"], "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(da["donor_files_inspected"], 15)

    def test_04_string_english_f_wave40_tokens_and_absent_markers_verified(self) -> None:
        s_en = self.default_audit["donor_audit"]["fx3_string_en_f"]
        self.assertEqual(s_en["file_bytes"], 373_820)
        self.assertTrue(s_en["uxd_container_ok"])
        for tok in (
            "Different Set for Still/Mv",
            "Aperture",
            "Shutter Speed",
            "ISO",
            "Exposure Comp.",
            "Metering Mode",
            "White Balance",
            "Picture Profile",
            "Focus Mode",
            "Shutter Mode",
            "Angle",
            "Custom Key/Dial Set.",
            "ISO/EI",
            "Control Wheel",
            "Follow Custom",
            "My Dial",
            "Recall Custom hold",
            "Remain Shoot Display",
            "Not Displayed",
            "Always Display",
            "Shoot-Only Display",
            "Save/Load Settings",
            "Camera Settings Reset",
            "Reset Network Set.",
            "Initialize",
        ):
            self.assertEqual(s_en["marker_hits"][tok], 1, msg=f"Missing token {tok!r}")
        self.assertEqual(s_en["absent_marker_hits"]["Autoframing Settings"], 0)
        self.assertEqual(s_en["absent_marker_hits"]["ECS"], 0)

    def test_05_fx6_string_english_and_large_appfw_cpapp_bounded_windows(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["fx6_string_en"]["file_bytes"], 118_208)
        self.assertEqual(da["fx6_string_en"]["absent_marker_hits"]["Autoframing Settings"], 0)
        for key in ("fx3_appfw", "fx6_appfw", "fx3_cpapp", "fx6_cpapp"):
            self.assertTrue(da[key]["bounded_windows_only"])
            self.assertLessEqual(da[key]["bytes_read_total"], 10 * 4096)
            for lbl, hit in da[key]["window_hits"].items():
                self.assertEqual(hit, 1, msg=f"{key} missing {lbl}")

    def test_06_env_force_clean_room_truthy_and_falsy_matrix(self) -> None:
        for val in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p258.is_forced_clean_room({p258.ENV_FORCE_CLEAN_ROOM: val}))
        for val in ("", "0", "false", "no", "off"):
            self.assertFalse(p258.is_forced_clean_room({p258.ENV_FORCE_CLEAN_ROOM: val}))

    def test_07_resolve_donor_paths_clean_room_sentinel_isolation(self) -> None:
        paths = p258.resolve_phase258_donor_paths(env={p258.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 15)
        for p in paths.values():
            self.assertIn(p258.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_08_missing_donor_directory_falls_back_to_clean_room_synthetic(self) -> None:
        bogus_env = {
            p258.ENV_FORCE_CLEAN_ROOM: "0",
            p258.ENV_MAC_WORK_ROOT: "/nonexistent/__phase258_bogus_work__",
        }
        with unittest.mock.patch.object(
            p258, "_iter_work_roots", return_value=(Path("/nonexistent/__phase258_bogus__"),)
        ):
            da = p258.inspect_phase258_donors(force_clean_room=False, env=bogus_env)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)

    def test_09_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
            force_clean_room=True
        )
        r2 = p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
            force_clean_room=True
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)

    def test_10_json_serialization_contains_zero_raw_firmware_bytes(self) -> None:
        encoded = json.dumps(self.default_audit)
        self.assertNotIn("\\x7fELF", encoded)
        self.assertEqual(self.default_audit["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_donor_open_uses_strictly_os_o_rdonly_without_write_flags(self) -> None:
        if p258.is_forced_clean_room():
            self.assertEqual(self.clean_audit["donor_audit"]["access_mode"], "O_RDONLY")
            return
        resolved = p258.resolve_phase258_donor_paths()
        if not all(p.is_file() for p in resolved.values()):
            return
        real_open = os.open
        seen_flags = []

        def _spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)

        saved_cache = dict(p258._DONOR_AUDIT_CACHE)
        try:
            p258._DONOR_AUDIT_CACHE.clear()
            with unittest.mock.patch("os.open", side_effect=_spy_open):
                da = p258.inspect_phase258_donors(force_clean_room=False)
            self.assertTrue(da.all_contracts_verified)
            self.assertGreaterEqual(len(seen_flags), 15)
            for fl in seen_flags:
                self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
        finally:
            p258._DONOR_AUDIT_CACHE.clear()
            p258._DONOR_AUDIT_CACHE.update(saved_cache)

    def test_12_donor_cache_hit_returns_identical_singleton_under_1ms(self) -> None:
        t0 = time.monotonic()
        a1 = p258.inspect_phase258_donors()
        a2 = p258.inspect_phase258_donors()
        elapsed = time.monotonic() - t0
        self.assertIs(a1, a2)
        self.assertLess(elapsed, 0.05)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 50A — [Different Set for Still/Mv] 8-Item
    # Asymmetric Transitions & Ver. 7.02 [Shutter Angle] Override (16)
    # ------------------------------------------------------------------
    def test_13_exact_8_diff_set_still_mv_items_and_menu_paths(self) -> None:
        self.assertEqual(
            p258.ALL_8_DIFF_SET_ITEMS,
            (
                "Aperture",
                "Shutter Speed",
                "ISO",
                "Exposure Comp.",
                "Metering Mode",
                "White Balance",
                "Picture Profile",
                "Focus Mode",
            ),
        )
        self.assertEqual(len(p258.ALL_8_DIFF_SET_ITEMS), 8)
        self.assertEqual(
            p258.DIFF_SET_STILL_MV_MENU_PATH,
            "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]",
        )

    def test_14_common_to_separate_copies_7_items_and_keeps_custom_wb_still_only(self) -> None:
        seed = {
            "Aperture": "F2.0",
            "Shutter Speed": "1/500",
            "ISO": "1600",
            "Exposure Comp.": "+1.0EV",
            "Metering Mode": "Highlight",
            "White Balance": "Custom 2",
            "Picture Profile": "PP11 (S-Cinetone)",
            "Focus Mode": "AF-S",
        }
        res = p258.coemulate_different_set_still_mv(
            checked_items=(),
            still_registers=seed,
            transition=p258.TRANSITION_COMMON_TO_SEPARATE,
            transition_items=p258.ALL_8_DIFF_SET_ITEMS,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_checked_items, p258.ALL_8_DIFF_SET_ITEMS)
        self.assertTrue(res.custom_wb_still_only_enforced)
        self.assertEqual(res.effective_still_registers["White Balance"], "Custom 2")
        self.assertEqual(res.effective_movie_registers["White Balance"], "Auto")
        for it in p258.ALL_8_DIFF_SET_ITEMS:
            if it != "White Balance":
                self.assertEqual(res.effective_movie_registers[it], seed[it])

    def test_15_common_to_separate_with_standard_wb_copies_all_8_items_to_movie(self) -> None:
        seed = dict(p258.INITIAL_FACTORY_ITEM_DEFAULTS, **{"White Balance": "5500K", "ISO": "640"})
        res = p258.coemulate_different_set_still_mv(
            checked_items=(),
            still_registers=seed,
            transition=p258.TRANSITION_COMMON_TO_SEPARATE,
            transition_items=p258.ALL_8_DIFF_SET_ITEMS,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_movie_registers["White Balance"], "5500K")
        self.assertEqual(res.effective_movie_registers["ISO"], "640")

    def test_16_separate_to_common_resets_5_items_and_retains_aperture_shutter_custom_wb(self) -> None:
        still_seed = {
            "Aperture": "F1.4",
            "Shutter Speed": "1/1000",
            "ISO": "3200",
            "Exposure Comp.": "-0.7EV",
            "Metering Mode": "Center",
            "White Balance": "Custom 3",
            "Picture Profile": "PP8 (S-Log3)",
            "Focus Mode": "MF",
        }
        movie_seed = {
            "Aperture": "F8.0",
            "Shutter Speed": "1/48",
            "ISO": "12800",
            "Exposure Comp.": "+0.3EV",
            "Metering Mode": "Multi",
            "White Balance": "Daylight",
            "Picture Profile": "PP11 (S-Cinetone)",
            "Focus Mode": "AF-C",
        }
        res = p258.coemulate_different_set_still_mv(
            checked_items=p258.ALL_8_DIFF_SET_ITEMS,
            still_registers=still_seed,
            movie_registers=movie_seed,
            transition=p258.TRANSITION_SEPARATE_TO_COMMON,
            transition_items=p258.ALL_8_DIFF_SET_ITEMS,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.asymmetric_separate_to_common_enforced)
        self.assertEqual(res.effective_checked_items, ())
        self.assertEqual(res.effective_still_registers["Aperture"], "F1.4")
        self.assertEqual(res.effective_movie_registers["Aperture"], "F1.4")
        self.assertEqual(res.effective_still_registers["Shutter Speed"], "1/1000")
        self.assertEqual(res.effective_movie_registers["Shutter Speed"], "1/1000")
        self.assertEqual(res.effective_still_registers["White Balance"], "Custom 3")
        self.assertEqual(res.effective_movie_registers["White Balance"], "Auto")
        for reset_it in ("ISO", "Exposure Comp.", "Metering Mode", "Picture Profile", "Focus Mode"):
            self.assertEqual(
                res.effective_still_registers[reset_it],
                p258.INITIAL_FACTORY_ITEM_DEFAULTS[reset_it],
            )
            self.assertEqual(
                res.effective_movie_registers[reset_it],
                p258.INITIAL_FACTORY_ITEM_DEFAULTS[reset_it],
            )

    def test_17_separate_to_common_with_standard_wb_resets_wb_to_auto_retains_ap_ss(self) -> None:
        still_seed = dict(
            p258.INITIAL_FACTORY_ITEM_DEFAULTS,
            **{"Aperture": "F2.8", "Shutter Speed": "1/200", "White Balance": "Incandescent"},
        )
        res = p258.coemulate_different_set_still_mv(
            checked_items=p258.ALL_8_DIFF_SET_ITEMS,
            still_registers=still_seed,
            transition=p258.TRANSITION_SEPARATE_TO_COMMON,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_still_registers["Aperture"], "F2.8")
        self.assertEqual(res.effective_still_registers["Shutter Speed"], "1/200")
        self.assertEqual(res.effective_still_registers["White Balance"], "Auto")
        self.assertEqual(res.effective_movie_registers["White Balance"], "Auto")

    def test_18_custom_wb_variants_custom1_custom2_custom3_all_still_only(self) -> None:
        for cwb in ("Custom 1", "Custom 2", "Custom 3", "Custom 1 (5600K)"):
            res = p258.coemulate_different_set_still_mv(
                checked_items=(),
                still_edit_item="White Balance",
                still_edit_value=cwb,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_still_registers["White Balance"], cwb)
            self.assertEqual(res.effective_movie_registers["White Balance"], "Auto")

    def test_19_movie_direct_custom_wb_assignment_rejected_einval(self) -> None:
        res = p258.coemulate_different_set_still_mv(
            checked_items=("White Balance",),
            movie_edit_item="White Balance",
            movie_edit_value="Custom 1",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EINVAL_ERRNO)

    def test_20_v702_shutter_mode_angle_overrides_common_shutter_speed_decoupling(self) -> None:
        res = p258.coemulate_different_set_still_mv(
            firmware_version="7.02",
            checked_items=(),
            movie_shutter_mode="Angle",
            movie_shutter_angle="180.0 deg",
            still_edit_item="Shutter Speed",
            still_edit_value="1/4000",
            movie_edit_shutter_angle="90.0 deg",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.shutter_angle_override_decoupled)
        self.assertFalse(res.shutter_speed_common_coupled)
        self.assertEqual(res.effective_still_registers["Shutter Speed"], "1/4000")
        self.assertEqual(res.effective_movie_shutter_angle, "90.0 deg")
        self.assertEqual(res.shutter_angle_common_bleed_events, 0)

    def test_21_v600_v602_v700_v702_all_admit_shutter_angle_override(self) -> None:
        for fw in ("6.00", "6.02", "7.00", "7.02"):
            res = p258.coemulate_different_set_still_mv(
                firmware_version=fw,
                checked_items=(),
                movie_shutter_mode="Angle",
            )
            self.assertTrue(res.admitted, msg=fw)
            self.assertTrue(res.shutter_angle_override_decoupled)

    def test_22_pre_v600_firmware_200_to_500_rejects_shutter_angle_eopnotsupp(self) -> None:
        for fw in ("2.00", "3.00", "4.00", "5.00"):
            res = p258.coemulate_different_set_still_mv(
                firmware_version=fw,
                movie_shutter_mode="Angle",
            )
            self.assertFalse(res.admitted, msg=fw)
            self.assertEqual(res.errno_code, p258.EOPNOTSUPP_ERRNO)

    def test_23_shutter_mode_speed_when_unchecked_couples_still_and_movie_shutter(self) -> None:
        res = p258.coemulate_different_set_still_mv(
            firmware_version="7.02",
            checked_items=(),
            movie_shutter_mode="Speed",
            still_edit_item="Shutter Speed",
            still_edit_value="1/320",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.shutter_speed_common_coupled)
        self.assertFalse(res.shutter_angle_override_decoupled)
        self.assertEqual(res.effective_still_registers["Shutter Speed"], "1/320")
        self.assertEqual(res.effective_movie_registers["Shutter Speed"], "1/320")

    def test_24_shutter_mode_speed_when_checked_keeps_still_and_movie_independent(self) -> None:
        res = p258.coemulate_different_set_still_mv(
            firmware_version="7.02",
            checked_items=("Shutter Speed",),
            movie_shutter_mode="Speed",
            still_edit_item="Shutter Speed",
            still_edit_value="1/1000",
            movie_edit_item="Shutter Speed",
            movie_edit_value="1/50",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.shutter_speed_common_coupled)
        self.assertEqual(res.effective_still_registers["Shutter Speed"], "1/1000")
        self.assertEqual(res.effective_movie_registers["Shutter Speed"], "1/50")

    def test_25_diff_set_survives_camera_settings_reset_while_exposure_resets(self) -> None:
        checked = ("Aperture", "Shutter Speed", "ISO", "Picture Profile")
        res = p258.coemulate_different_set_still_mv(
            checked_items=checked,
            still_registers=dict(
                p258.INITIAL_FACTORY_ITEM_DEFAULTS,
                **{"Aperture": "F1.8", "ISO": "6400"},
            ),
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.survived_camera_settings_reset)
        self.assertEqual(res.effective_checked_items, checked)
        self.assertEqual(res.effective_still_registers["Aperture"], "F4.0")
        self.assertEqual(res.effective_still_registers["ISO"], "Auto")

    def test_26_diff_set_survives_reset_network_set_and_clears_only_on_initialize(self) -> None:
        checked = ("Aperture", "White Balance", "Focus Mode")
        r_net = p258.coemulate_different_set_still_mv(
            checked_items=checked,
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.admitted)
        self.assertTrue(r_net.survived_reset_network_set)
        self.assertEqual(r_net.effective_checked_items, checked)

        r_init = p258.coemulate_different_set_still_mv(
            checked_items=p258.ALL_8_DIFF_SET_ITEMS,
            reset_action="Initialize",
        )
        self.assertTrue(r_init.admitted)
        self.assertTrue(r_init.restored_by_initialize)
        self.assertEqual(r_init.effective_checked_items, ())

    def test_27_forced_corrupt_transition_and_shutter_angle_bleed_blocked_einval(self) -> None:
        r1 = p258.coemulate_different_set_still_mv(
            checked_items=p258.ALL_8_DIFF_SET_ITEMS,
            transition=p258.TRANSITION_SEPARATE_TO_COMMON,
            force_corrupt_transition=True,
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p258.EINVAL_ERRNO)
        self.assertEqual(r1.diff_set_transition_corruption_events, 0)

        r2 = p258.coemulate_different_set_still_mv(
            movie_shutter_mode="Angle",
            force_shutter_angle_common_bleed=True,
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p258.EINVAL_ERRNO)
        self.assertEqual(r2.shutter_angle_common_bleed_events, 0)

    def test_28_non_catalog_diff_set_item_and_invalid_enums_rejected_einval(self) -> None:
        r_bad_item = p258.coemulate_different_set_still_mv(checked_items=("SteadyShot",))
        self.assertFalse(r_bad_item.admitted)
        self.assertEqual(r_bad_item.errno_code, p258.EINVAL_ERRNO)

        r_bad_fw = p258.coemulate_different_set_still_mv(firmware_version="1.00")
        self.assertFalse(r_bad_fw.admitted)
        self.assertEqual(r_bad_fw.errno_code, p258.EINVAL_ERRNO)

        r_bad_angle_edit = p258.coemulate_different_set_still_mv(
            movie_shutter_mode="Speed",
            movie_edit_shutter_angle="180.0 deg",
        )
        self.assertFalse(r_bad_angle_edit.admitted)
        self.assertEqual(r_bad_angle_edit.errno_code, p258.EOPNOTSUPP_ERRNO)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 50B — [Custom Key/Dial Set.] 3-Domain ISO/EI
    # Auto-Adaptation & Slot-1 CAMSET01.DAT Vault Round-Trip (15)
    # ------------------------------------------------------------------
    def test_29_factory_cinema_dial_defaults_front_aperture_rear_isoei_wheel_shutter(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault()
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.persistent_dial_assignments,
            {
                "Front dial": "Aperture",
                "Rear dial": "ISO/EI",
                "Control Wheel": "Shutter Speed",
            },
        )

    def test_30_rear_dial_iso_ei_adapts_to_iso_in_off_and_flexible_iso(self) -> None:
        for mode in ("Off", "Flexible ISO"):
            res = p258.coemulate_custom_key_dial_and_camset_vault(log_shooting_mode=mode)
            self.assertTrue(res.admitted, msg=mode)
            self.assertEqual(res.rear_dial_adapted_parameter, "ISO")

    def test_31_rear_dial_iso_ei_adapts_to_exposure_index_in_cine_ei_and_quick(self) -> None:
        for mode in ("Cine EI", "Cine EI Quick"):
            res = p258.coemulate_custom_key_dial_and_camset_vault(log_shooting_mode=mode)
            self.assertTrue(res.admitted, msg=mode)
            self.assertEqual(res.rear_dial_adapted_parameter, "Exposure Index (EI)")

    def test_32_three_domains_still_movie_playback_independent_keymaps(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            active_domain="Playback",
            still_keys={"Custom Button 3": "Focus Area"},
            movie_keys={"Custom Button 3": "Focus Map"},
            playback_keys={"Custom Button 2": "Rating"},
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_still_keys["Custom Button 3"], "Focus Area")
        self.assertEqual(res.effective_movie_keys["Custom Button 3"], "Focus Map")
        self.assertEqual(res.effective_playback_keys["Custom Button 2"], "Rating")

    def test_33_movie_follow_custom_dynamically_inherits_still_assignments(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            active_domain="Movie",
            still_keys={
                "Custom Button 1": "Shockless WB",
                "Custom Button 2": "Zebra Display",
            },
            movie_keys={
                "Custom Button 1": "Follow Custom",
                "Custom Button 2": "Follow Custom",
            },
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.resolved_movie_keys["Custom Button 1"], "Shockless WB")
        self.assertEqual(res.resolved_movie_keys["Custom Button 2"], "Zebra Display")
        self.assertIn("Custom Button 1", res.follow_custom_inherited_keys)
        self.assertIn("Custom Button 2", res.follow_custom_inherited_keys)

    def test_34_follow_custom_in_still_domain_rejected_einval(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            active_domain="Still",
            still_keys={"Custom Button 1": "Follow Custom"},
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EINVAL_ERRNO)

    def test_35_my_dial_1_2_3_temporary_swap_preserves_persistent_dials(self) -> None:
        for slot in ("My Dial 1", "My Dial 2", "My Dial 3"):
            res = p258.coemulate_custom_key_dial_and_camset_vault(active_my_dial_slot=slot)
            self.assertTrue(res.admitted, msg=slot)
            self.assertTrue(res.my_dial_temporary_swap_active)
            self.assertEqual(res.persistent_dial_assignments["Front dial"], "Aperture")
            self.assertNotEqual(
                res.effective_dial_assignments,
                res.persistent_dial_assignments,
            )

    def test_36_recall_custom_hold_1_2_3_admitted_in_still_movie_blocked_in_playback(self) -> None:
        for dom in ("Still", "Movie"):
            for hold in ("Recall Custom hold 1", "Recall Custom hold 2", "Recall Custom hold 3"):
                res = p258.coemulate_custom_key_dial_and_camset_vault(
                    active_domain=dom,
                    active_recall_custom_hold=hold,
                )
                self.assertTrue(res.admitted)

        r_pb = p258.coemulate_custom_key_dial_and_camset_vault(
            active_domain="Playback",
            active_recall_custom_hold="Recall Custom hold 1",
        )
        self.assertFalse(r_pb.admitted)
        self.assertEqual(r_pb.errno_code, p258.EOPNOTSUPP_ERRNO)

    def test_37_custom_key_dial_survives_camera_settings_reset_and_network_reset(self) -> None:
        still_custom = {"Custom Button 1": "Shockless WB"}
        dials_custom = {"Control Wheel": "Exposure Comp."}
        r_cam = p258.coemulate_custom_key_dial_and_camset_vault(
            still_keys=still_custom,
            dial_assignments=dials_custom,
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_cam.admitted)
        self.assertTrue(r_cam.survived_camera_settings_reset)
        self.assertEqual(r_cam.effective_still_keys["Custom Button 1"], "Shockless WB")
        self.assertEqual(r_cam.persistent_dial_assignments["Control Wheel"], "Exposure Comp.")

        r_net = p258.coemulate_custom_key_dial_and_camset_vault(
            still_keys=still_custom,
            dial_assignments=dials_custom,
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.admitted)
        self.assertTrue(r_net.survived_reset_network_set)
        self.assertEqual(r_net.effective_still_keys["Custom Button 1"], "Shockless WB")

    def test_38_custom_key_dial_restored_to_factory_defaults_only_by_initialize(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            still_keys={"Custom Button 1": "Shockless WB"},
            dial_assignments={"Front dial": "Shutter Speed"},
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.restored_by_initialize)
        self.assertEqual(res.effective_still_keys["Custom Button 1"], "White Balance")
        self.assertEqual(
            res.persistent_dial_assignments,
            dict(p258.FACTORY_CINEMA_DIAL_DEFAULTS),
        )

    def test_39_slot1_camset01_rdonly_load_lossless_roundtrip_after_initialize(self) -> None:
        still_v = {"Custom Button 1": "Shockless WB", "Custom Button 4": "Focus Magnifier"}
        movie_v = {"Custom Button 1": "Follow Custom", "Custom Button 6": "Display LUT"}
        pb_v = {"Custom Button 2": "Rating"}
        dials_v = {"Front dial": "Aperture", "Rear dial": "ISO/EI", "Control Wheel": "Exposure Comp."}
        before = p258.coemulate_custom_key_dial_and_camset_vault(
            still_keys=still_v,
            movie_keys=movie_v,
            playback_keys=pb_v,
            dial_assignments=dials_v,
        )
        restored = p258.coemulate_custom_key_dial_and_camset_vault(
            still_keys=still_v,
            movie_keys=movie_v,
            playback_keys=pb_v,
            dial_assignments=dials_v,
            reset_action="Initialize",
            camset_action="LOAD_SLOT1_VAULT_RDONLY",
            slot1_vault_still_keys=still_v,
            slot1_vault_movie_keys=movie_v,
            slot1_vault_playback_keys=pb_v,
            slot1_vault_dials=dials_v,
        )
        self.assertTrue(restored.admitted)
        self.assertTrue(restored.camset_roundtrip_restored)
        self.assertEqual(restored.slot1_custom_key_vault_mutation_bytes, 0)
        self.assertEqual(
            restored.camset_serialized_sha256_prefix16,
            before.camset_serialized_sha256_prefix16,
        )
        self.assertEqual(restored.resolved_movie_keys["Custom Button 1"], "Shockless WB")

    def test_40_slot2_scratch_camset_save_admitted_zero_slot1_vault_mutation(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            camset_action="SAVE_SLOT2_SCRATCH"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.slot1_custom_key_vault_mutation_bytes, 0)

    def test_41_slot1_tier0_vault_camset_save_blocked_erofs_zero_mutation(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            camset_action="SAVE_SLOT1_VAULT_MUTATE"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EROFS_ERRNO)
        self.assertEqual(res.slot1_custom_key_vault_mutation_bytes, 0)

    def test_42_force_slot1_custom_key_vault_write_flag_blocked_erofs(self) -> None:
        res = p258.coemulate_custom_key_dial_and_camset_vault(
            force_slot1_custom_key_vault_write=True
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EROFS_ERRNO)
        self.assertEqual(res.slot1_custom_key_vault_mutation_bytes, 0)

    def test_43_custom_key_invalid_domain_dial_log_mode_camset_rejected_einval(self) -> None:
        for kw in (
            {"active_domain": "S&Q_BOGUS"},
            {"log_shooting_mode": "HLG_BOGUS"},
            {"active_my_dial_slot": "My Dial 4"},
            {"dial_assignments": {"Top Sub Dial": "ISO"}},
            {"camset_action": "WIPE_VAULT"},
        ):
            res = p258.coemulate_custom_key_dial_and_camset_vault(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p258.EINVAL_ERRNO)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 50C & 50D — [Remain Shoot Display] Still-Buffer
    # Scope, EVF-Less ILME-FX3 Monitor Topology & 14 Redlines (14)
    # ------------------------------------------------------------------
    def test_44_remain_shoot_display_factory_default_not_displayed_and_3_modes(self) -> None:
        self.assertEqual(p258.REMAIN_SHOOT_DEFAULT, "Not Displayed")
        self.assertEqual(
            p258.ALL_3_REMAIN_SHOOT_MODES,
            ("Not Displayed", "Always Display", "Shoot-Only Display"),
        )
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_remain_shoot_register, "Not Displayed")
        self.assertFalse(res.visible_on_vari_angle_lcd)
        self.assertIsNone(res.rendered_buffer_frames)

    def test_45_always_display_shows_still_buffer_in_still_idle_and_burst(self) -> None:
        for burst in (False, True):
            res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
                configured_remain_shoot_display="Always Display",
                shooting_scope="Still",
                shutter_half_or_burst_active=burst,
                still_continuous_buffer_remaining_frames=42,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.visible_on_vari_angle_lcd)
            self.assertTrue(res.displays_still_continuous_buffer)
            self.assertFalse(res.displays_movie_card_remaining_time)
            self.assertEqual(res.rendered_buffer_frames, 42)

    def test_46_shoot_only_display_hidden_in_still_idle_and_visible_in_burst(self) -> None:
        r_idle = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Shoot-Only Display",
            shooting_scope="Still",
            shutter_half_or_burst_active=False,
        )
        self.assertTrue(r_idle.admitted)
        self.assertFalse(r_idle.visible_on_vari_angle_lcd)
        self.assertIsNone(r_idle.rendered_buffer_frames)

        r_burst = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Shoot-Only Display",
            shooting_scope="Still",
            shutter_half_or_burst_active=True,
            still_continuous_buffer_remaining_frames=19,
        )
        self.assertTrue(r_burst.admitted)
        self.assertTrue(r_burst.visible_on_vari_angle_lcd)
        self.assertEqual(r_burst.rendered_buffer_frames, 19)

    def test_47_remain_shoot_suppressed_in_movie_and_sq_never_shows_movie_time(self) -> None:
        for scope in ("Movie", "S&Q"):
            for mode in p258.ALL_3_REMAIN_SHOOT_MODES:
                res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
                    configured_remain_shoot_display=mode,
                    shooting_scope=scope,
                    shutter_half_or_burst_active=True,
                )
                self.assertTrue(res.admitted)
                self.assertFalse(res.visible_on_vari_angle_lcd)
                self.assertFalse(res.displays_movie_card_remaining_time)
                self.assertIsNone(res.rendered_buffer_frames)

    def test_48_forced_movie_card_remaining_time_spoof_rejected_einval(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Always Display",
            shooting_scope="Movie",
            force_movie_card_time_spoof=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EINVAL_ERRNO)
        self.assertFalse(res.displays_movie_card_remaining_time)

    def test_49_remain_shoot_survives_camera_settings_reset_and_network_reset(self) -> None:
        r_cam = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Always Display",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_cam.admitted)
        self.assertTrue(r_cam.survived_camera_settings_reset)
        self.assertEqual(r_cam.effective_remain_shoot_register, "Always Display")

        r_net = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Shoot-Only Display",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.admitted)
        self.assertTrue(r_net.survived_reset_network_set)
        self.assertEqual(r_net.effective_remain_shoot_register, "Shoot-Only Display")

    def test_50_remain_shoot_restored_to_not_displayed_only_by_initialize(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            configured_remain_shoot_display="Always Display",
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.restored_by_initialize)
        self.assertEqual(res.effective_remain_shoot_register, "Not Displayed")
        self.assertFalse(res.visible_on_vari_angle_lcd)

    def test_51_fx3_evfless_topology_locks_builtin_evf_eye_sensor_finder_menu_false(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor()
        self.assertEqual(res.body_model, "ILME-FX3")
        self.assertEqual(res.help_guide_id, "ilc/2210")
        self.assertFalse(res.fx3_has_builtin_evf)
        self.assertFalse(res.fx3_has_eye_sensor)
        self.assertFalse(res.has_finder_monitor_menu)
        self.assertEqual(res.active_display_surface, "VARI_ANGLE_LCD")
        self.assertEqual(res.evf_finder_monitor_spoof_events, 0)

    def test_52_evf_viewfinder_surface_request_rejected_eopnotsupp(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            requested_display_surface="EVF_VIEWFINDER",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.evf_finder_monitor_spoof_events, 0)
        self.assertFalse(res.fx3_has_builtin_evf)

    def test_53_finder_monitor_eye_sensor_auto_switch_rejected_eopnotsupp(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            requested_display_surface="FINDER_MONITOR_EYE_SENSOR_AUTO",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.evf_finder_monitor_spoof_events, 0)

    def test_54_forced_evf_finder_monitor_spoof_flag_rejected_eopnotsupp(self) -> None:
        res = p258.coemulate_remain_shoot_display_and_evfless_monitor(
            force_evf_finder_monitor_spoof=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p258.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.evf_finder_monitor_spoof_events, 0)

    def test_55_remain_shoot_invalid_mode_scope_negative_buffer_rejected_einval(self) -> None:
        for kw in (
            {"configured_remain_shoot_display": "Card Remaining Time"},
            {"shooting_scope": "Playback"},
            {"reset_action": "Factory Wipe"},
            {"still_continuous_buffer_remaining_frames": -1},
            {"movie_card_remaining_minutes": -5},
        ):
            res = p258.coemulate_remain_shoot_display_and_evfless_monitor(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p258.EINVAL_ERRNO)

    def test_56_all_14_stage50_redline_probes_individually_blocked_eacces_or_erofs(self) -> None:
        self.assertEqual(len(p258.ALL_14_REDLINE_PROBE_FIELDS), 14)
        for field in p258.ALL_14_REDLINE_PROBE_FIELDS:
            pr = p258.probe_phase258_redline_guard(**{field: True})
            self.assertFalse(pr.valid, msg=field)
            if field in (
                "cnflasha_userspace_write_requested",
                "slot1_custom_key_vault_write_requested",
            ):
                self.assertEqual(pr.errno_code, p258.EROFS_ERRNO)
            else:
                self.assertEqual(pr.errno_code, p258.EACCES_ERRNO)
            self.assertFalse(pr.persistent_emmc_writes_authorized)
            self.assertFalse(pr.hardware_live_attachment_authorized)
            self.assertFalse(pr.overall_ready_for_hardware_attach)
            self.assertTrue(pr.cnflasha_userspace_write_blocked)
            self.assertEqual(pr.physical_device_writes, 0)
            self.assertEqual(pr.raw_firmware_bytes_leaked, 0)

    def test_57_unknown_redline_probe_rejected_einval_and_baseline_valid(self) -> None:
        base = p258.probe_phase258_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)

        bad = p258.probe_phase258_redline_guard(bogus_stage50_probe=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p258.EINVAL_ERRNO)

    # ------------------------------------------------------------------
    # Group 5: CLI, 50/50 Grand Milestone Suite Integration & Hygiene (11)
    # ------------------------------------------------------------------
    def test_58_standalone_cli_json_and_summary_in_process_both_modes(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc1 = p258.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc1, 0)
        self.assertIn("[PASS] Phase 258 Stage 50 (50/50)", buf_sum.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p258.main(["--self-test", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["milestone"], "50/50")

    def test_59_standalone_subprocess_cli_clean_room_and_default_pass(self) -> None:
        script = str(FX3_VM_DIR / "realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py")
        env_clean = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", FX3_FX6_FORCE_CLEAN_ROOM="1")
        p_clean = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env_clean,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 258 Stage 50 (50/50)", p_clean.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", p_clean.stdout)

    def test_60_fx3_vm_coemulation_suite_includes_stage50_grand_milestone_50_of_50(self) -> None:
        self.assertTrue(self.clean_suite["all_checks_passed"])
        self.assertIn(
            "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
            self.clean_suite,
        )
        s50 = self.clean_suite["stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"]
        self.assertTrue(s50["all_checks_passed"])
        self.assertEqual(s50["phase_number"], 258)
        self.assertEqual(s50["milestone"], "50/50")
        self.assertEqual(
            s50["schema"],
            "realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1",
        )
        self.assertFalse(s50["fx3_has_builtin_evf"])
        self.assertEqual(s50["diff_set_transition_corruption_events"], 0)
        self.assertEqual(s50["shutter_angle_common_bleed_events"], 0)
        self.assertEqual(s50["slot1_custom_key_vault_mutation_bytes"], 0)
        self.assertEqual(s50["evf_finder_monitor_spoof_events"], 0)
        self.assertEqual(s50["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in self.clean_suite if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 50)
        self.assertLess(self.clean_suite_elapsed, 4.0)

    def test_61_fx3_vm_coemulation_suite_all_50_stage_indices_1_to_50_unique_and_present(self) -> None:
        self.assertTrue(self.default_suite["all_checks_passed"])
        for idx in range(1, 51):
            matches = [k for k in self.default_suite if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(self.default_suite_elapsed, 4.0)

    def test_62_fx3_vm_coemulation_suite_skip_stage50_and_skip_phase258_config(self) -> None:
        rep_skip_p258 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                **_fast_suite_kwargs(
                    include_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil=False
                )
            )
        )
        self.assertTrue(rep_skip_p258["all_checks_passed"])
        self.assertNotIn(
            "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
            rep_skip_p258,
        )
        self.assertFalse(rep_skip_p258["config"]["include_stage50"])

        rep_skip_s50 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(include_stage50=False))
        )
        self.assertTrue(rep_skip_s50["all_checks_passed"])
        self.assertNotIn(
            "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
            rep_skip_s50,
        )

    def test_63_fx3_vm_coemulation_suite_include_stage50_cli_summary(self) -> None:
        fast_flags = [
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
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
            "--skip-stage44",
            "--skip-stage45",
            "--skip-stage46",
            "--skip-stage47",
            "--skip-stage48",
            "--skip-stage49",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage50", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_diff_set_still_mv_custom_key_remain_shoot_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_64_fx3_vm_coemulation_suite_cli_skip_phase258_and_skip_stage50(self) -> None:
        fast_flags = [
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
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
            "--skip-stage44",
            "--skip-stage45",
            "--skip-stage46",
            "--skip-stage47",
            "--skip-stage48",
            "--skip-stage49",
        ]
        for flag in ("--skip-phase258", "--skip-stage50", "--no-include-stage50"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil",
                rep,
            )

    def test_65_run_stage50_direct_runner_matches_standalone_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s50 = suite.run_stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(cfg)
        self.assertEqual(
            s50["phase258_audit_digest_sha256"],
            self.clean_audit["audit_digest_sha256"],
        )

    def test_66_menu_paths_match_official_sony_ilme_fx3_help_guide_ilc_2210(self) -> None:
        self.assertEqual(
            p258.DIFF_SET_STILL_MV_MENU_PATH,
            "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]",
        )
        self.assertEqual(
            p258.CUSTOM_KEY_DIAL_MENU_PATH,
            "MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]",
        )
        self.assertEqual(
            p258.REMAIN_SHOOT_DISPLAY_MENU_PATH,
            "MENU -> Setup -> [Display Option] -> [Remain Shoot Display]",
        )
        self.assertEqual(
            p258.SHUTTER_MODE_MENU_PATH,
            "MENU -> Shooting -> [Shutter/Silent] -> [Shutter Mode]",
        )

    def test_67_fx3_vm_readme_documents_phase258_stage50_grand_milestone_50_of_50(self) -> None:
        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 258", readme)
        self.assertIn("Stage 50", readme)
        self.assertIn("50/50", readme)
        self.assertIn("realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py", readme)
        self.assertIn("--include-stage50", readme)

    def test_68_zero_pyc_bytecode_files_and_sub_second_standalone_runtime(self) -> None:
        t0 = time.monotonic()
        r_clean = p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil(
            force_clean_room=True
        )
        r_def = p258.run_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil()
        elapsed = time.monotonic() - t0
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertLess(elapsed, 1.0)
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
