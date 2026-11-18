#!/usr/bin/env python3
"""Unit tests for Phase 285 (Stage 57, 57/57):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-47
`[USB Connection Mode]` 4-Mode vs Dormant `NOUVC` `[USB Streaming]` Split & `[USB LUN Setting]` /
`[USB Power Supply]` Data-Isolated PD HIL,
`[HDMI Info. Display]` LCD-Blanking vs Clean-Feed & `1080` Log/`PPLUT` Clamp vs `4K` `RAW` /
`Off(HDMI Only)` Auto-Clean-Feed Override HIL, and
`[Protect]` 4-Scope vs `[Format]` Wipe (`Slot-1` Dual-Layer Hardware SD `WP` + Firewall) &
`[Reset Network Set.]` Auto-Reboot + Post-Reboot `[Airplane Mode] = [On]` HIL Co-Emulator
(76 dual-mode tests).
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
import realhw_usb_mode_hdmi_info_protect_network_reset_coemulator as p285  # noqa: E402

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
        include_stage56=False,
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
]


class TestPhase285Stage57Wave47HilCoEmulator(unittest.TestCase):
    """76 dual-mode tests for Phase 285 Stage 57 (57/57)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_audit = p285.run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil()
        cls.clean_audit = p285.run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil(
            force_clean_room=True
        )
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite()
        cls.default_suite_elapsed = time.monotonic() - t0

        t1 = time.monotonic()
        cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Redlines & Dual-Mode 13-Donor O_RDONLY Audit (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_phase_and_milestone_constants(self) -> None:
        self.assertEqual(p285.SCHEMA_ID, "realhw_usb_mode_hdmi_info_protect_network_reset_coemulator_v1")
        self.assertEqual(p285.PHASE_285_SCHEMA, p285.SCHEMA_ID)
        self.assertEqual(p285.PHASE_285_VERSION, "285.0.0")
        self.assertEqual(p285.PHASE_NUMBER, 285)
        self.assertEqual(p285.STAGE_INDEX, 57)
        self.assertEqual(p285.STAGE_TOTAL, 57)
        self.assertEqual(p285.MILESTONE_LABEL, "57/57")
        self.assertEqual(p285.STAGE_NAME, "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil")
        self.assertEqual(p285.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p285.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p285.FX3_HELP_GUIDE_ID, "ilc/2210")

    def test_02_hard_safety_redline_constants_locked(self) -> None:
        self.assertTrue(p285.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p285.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(p285.SLOT1_FORMAT_HARD_LOCKED)
        self.assertFalse(p285.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p285.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p285.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p285.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p285.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p285.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p285.FX3_UI_EXPOSES_NATIVE_USB_STREAMING)
        self.assertFalse(p285.USB_F_UVC_INSMOD_AT_FX3_BOOT)
        for zero_val in (
            p285.NOP_COUNT,
            p285.GUEST_CODE_MODIFICATION_BYTES,
            p285.CP_MUTATION_BYTES,
            p285.WBI_MUTATION_BYTES,
            p285.CALIBRATION_MUTATION_BYTES,
            p285.CNFLASHA_MUTATION_BYTES,
            p285.NVRAM_PERSISTENT_WRITES,
            p285.BK4_PERSISTENT_NVRAM_WRITES,
            p285.PHYSICAL_DEVICE_WRITES,
            p285.EMMC_NFLASHA_WRITE_COUNT,
            p285.EMMC_MUTATION_BYTES,
            p285.EMMC_CORRUPTIONS,
            p285.SPI_NOR_MUTATION_BYTES,
            p285.OTP_FUSE_TOUCHES,
            p285.RPMB_COUNTER_INCREMENTS,
            p285.FX3_NATIVE_UVC_SPOOF_EVENTS,
            p285.TIER0_USB_DATA_ENUMERATION_VIOLATIONS,
            p285.PHYSICAL_USB_PACKETS_EMITTED,
            p285.HDMI_OSD_OR_CLAMP_BYPASS_EVENTS,
            p285.HDMI_CLEAN_FEED_OVERRIDE_VIOLATIONS,
            p285.SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
            p285.POST_RESET_AIRPLANE_OFF_RF_LEAK_EVENTS,
            p285.PASSIVE_TX_BYTES_EMITTED,
            p285.RSV_ORPHAN_COUNT,
            p285.WF12_00342260_HITS,
            p285.APPFW_CRASHES,
            p285.NULL_GPIO_DEREFS,
            p285.MAILBOX_STALLS,
            p285.STOCK_CP_FAULT_COUNT,
            p285.RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_val, 0)

    def test_03_default_and_clean_room_reports_both_pass(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p285.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.default_audit["donor_audit"]["donor_files_inspected"], 13)
        self.assertEqual(self.clean_audit["donor_audit"]["donor_files_inspected"], 13)
        self.assertEqual(self.default_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.clean_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_04_clean_room_deterministic_digest_and_zero_leak(self) -> None:
        rep_a = p285.run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil(
            force_clean_room=True
        )
        rep_b = p285.run_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil(
            force_clean_room=True
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])
        self.assertEqual(len(rep_a["audit_digest_sha256"]), 64)
        self.assertEqual(rep_a["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_is_forced_clean_room_honors_both_env_vars(self) -> None:
        self.assertFalse(p285.is_forced_clean_room(env={}))
        self.assertTrue(p285.is_forced_clean_room(env={p285.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p285.is_forced_clean_room(env={p285.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p285.is_forced_clean_room(env={p285.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertFalse(p285.is_forced_clean_room(env={p285.ENV_FORCE_CLEAN_ROOM: "0"}))

    def test_06_clean_room_parity_when_donor_roots_missing(self) -> None:
        missing = {
            k: REPO_ROOT / "nonexistent_p285_dir" / rel
            for k, rel in p285.DONOR_RELPATHS.items()
        }
        with unittest.mock.patch.object(p285, "resolve_phase285_donor_paths", return_value=missing):
            audit = p285.inspect_phase285_donors(env={})
        self.assertEqual(audit.source_mode, p285.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 13)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_13_donor_exact_byte_sizes_in_both_modes(self) -> None:
        self.assertEqual(len(p285.EXPECTED_DONOR_BYTES), 13)
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            for key, exp_bytes in p285.EXPECTED_DONOR_BYTES.items():
                self.assertEqual(da[key]["file_bytes"], exp_bytes, msg=key)

    def test_08_compact_donor_sha256_and_container_checks(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            for key in p285.EXPECTED_COMPACT_DONOR_SHA256:
                self.assertTrue(da[key]["sha256_verified"], msg=key)
                if key.endswith("uvc"):
                    self.assertTrue(da[key]["elf64_le_ok"], msg=key)
                else:
                    self.assertTrue(da[key]["uxd_container_ok"], msg=key)

    def test_09_large_donor_head4k_and_bounded_windows_verified(self) -> None:
        for rep in (self.default_audit, self.clean_audit):
            da = rep["donor_audit"]
            for key in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
                self.assertTrue(da[key]["head_sha256_verified"], msg=key)
                self.assertTrue(da[key]["bounded_windows_only"], msg=key)
                self.assertGreater(da[key]["bytes_read_total"], 0, msg=key)
                self.assertTrue(all(v == 1 for v in da[key]["window_hits"].values()), msg=key)
            self.assertTrue(da["fx3_appfw"]["elf64_le_ok"])
            self.assertTrue(da["fx6_appfw"]["elf64_le_ok"])

    def test_10_4lang_uxc_wave47_tokens_all_present(self) -> None:
        da = self.default_audit["donor_audit"]
        for key in ("fx3_string_en_f", "fx3_string_sc_f", "fx3_string_tc_f", "fx3_string_ja_f"):
            hits = da[key]["marker_hits"]
            self.assertTrue(all(v == 1 for v in hits.values()), msg=f"{key}:{hits}")

    def test_11_fx3_vs_fx6_donor_wave47_contrast_markers_proven(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["usb_mode_nouvc_split_proven"])
        self.assertTrue(da["hdmi_info_cleanfeed_proven"])
        self.assertTrue(da["protect_format_netreset_proven"])
        self.assertEqual(da["fx3_usb_f_uvc"]["file_bytes"], 78_840)
        self.assertEqual(da["fx6_usb_f_uvc"]["file_bytes"], 78_840)
        self.assertEqual(da["fx3_appfw"]["window_hits"]["USB_METHOD_MASS_STRAGE"], 1)
        self.assertEqual(da["fx6_appfw"]["window_hits"]["FX6_USB_STREAM_PROCAM"], 1)

    def test_12_donor_inspection_sub_02s_cold_budget(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertLess(da["inspection_elapsed_s"], 0.2)
        self.assertEqual(da["access_mode"], "O_RDONLY")

    def test_13_resolve_donor_paths_clean_room_returns_sentinel_directory(self) -> None:
        resolved = p285.resolve_phase285_donor_paths(env={p285.ENV_FORCE_CLEAN_ROOM: "1"})
        for key, p in resolved.items():
            self.assertIn(p285.CLEAN_ROOM_SENTINEL_DIRNAME, str(p), msg=key)

    def test_14_fx3_string_en_and_en_g_distinct_wave47_markers(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertEqual(da["fx3_string_en"]["marker_hits"]["Protect"], 1)
        self.assertEqual(da["fx3_string_en"]["marker_hits"]["All Images in This Group"], 1)
        self.assertEqual(da["fx3_string_en"]["marker_hits"]["Format"], 1)
        self.assertEqual(da["fx3_string_en_g"]["marker_hits"]["External Output"], 1)
        self.assertEqual(da["fx3_string_en_g"]["marker_hits"]["USB Streaming"], 1)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 57A — [USB Connection Mode] 4-Mode vs NOUVC &
    #          Data-Isolated PD HIL (18 tests)
    # ------------------------------------------------------------------
    def test_15_fx3_exposes_exact_4_usb_connection_modes_and_factory_defaults(self) -> None:
        self.assertEqual(len(p285.FX3_EXPOSED_USB_CONNECTION_MODES), 4)
        self.assertEqual(
            p285.FX3_EXPOSED_USB_CONNECTION_MODES,
            (
                "Sel. When Connect",
                "MassStorage(MSC)",
                "MTP",
                "Remote Shoot (PC Remote)",
            ),
        )
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(tier0_airgapped_bench=False)
        self.assertTrue(r.admitted)
        self.assertEqual(r.menu_path, p285.USB_CONNECTION_MODE_MENU_PATH)
        self.assertEqual(r.effective_usb_connection_mode, "Sel. When Connect")
        self.assertEqual(r.effective_usb_lun_setting, "Multi")
        self.assertEqual(r.effective_usb_power_supply, "On")
        self.assertFalse(r.fx3_ui_exposes_native_usb_streaming)
        self.assertFalse(r.usb_f_uvc_insmod_at_fx3_boot)

    def test_16_fx3_usb_mode_resid16_and_usb_vid_pid_contracts(self) -> None:
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["Sel. When Connect"]["resid16"], "0x7738")
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["MassStorage(MSC)"]["resid16"], "0x6c54")
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["MassStorage(MSC)"]["usb_vid_pid"], "054C:0DA1")
        self.assertEqual(
            p285.USB_CONNECTION_MODE_SPEC["MassStorage(MSC)"]["internal_marker"],
            "USB_CONNECTION_METHOD_MASS_STRAGE",
        )
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["MTP"]["resid16"], "0xe24b")
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["MTP"]["slot_target"], "Slot 1")
        self.assertEqual(p285.USB_CONNECTION_MODE_SPEC["Remote Shoot (PC Remote)"]["resid16"], "0x60aa")

    def test_17_fx3_and_fx3a_reject_spoofed_native_usb_streaming_eopnotsupp(self) -> None:
        for body in (p285.BODY_MODEL_FX3, p285.BODY_MODEL_FX3A):
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
                body_profile=body,
                requested_usb_connection_mode=p285.USB_MODE_DORMANT_STREAMING,
                tier0_airgapped_bench=False,
            )
            self.assertFalse(r.admitted, msg=body)
            self.assertEqual(r.errno_code, p285.EOPNOTSUPP_ERRNO, msg=body)
            self.assertEqual(r.reason_code, "FX3_NOUVC_NATIVE_USB_STREAMING_MASKED", msg=body)
            self.assertEqual(r.fx3_native_uvc_spoof_events, 0, msg=body)
            self.assertFalse(r.fx3_ui_exposes_native_usb_streaming, msg=body)
            self.assertFalse(r.usb_f_uvc_insmod_at_fx3_boot, msg=body)

    def test_18_fx6_procam_uvc_and_sibling_bodies_model_uvc_contrast(self) -> None:
        for body in (
            p285.BODY_MODEL_FX6,
            p285.BODY_MODEL_FX30,
            p285.BODY_MODEL_FX2,
            p285.BODY_MODEL_A7M4,
            p285.BODY_MODEL_ZVE1,
        ):
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
                body_profile=body,
                requested_usb_connection_mode=p285.USB_MODE_DORMANT_STREAMING,
                usb_port=p285.USB_PORT_TYPE_C,
                tier0_airgapped_bench=False,
                usb_data_lines_physically_isolated=False,
            )
            self.assertTrue(r.admitted, msg=body)
            self.assertEqual(r.effective_usb_connection_mode, "USB Streaming", msg=body)
            self.assertEqual(r.fx6_procam_uvc_bkid, "BKID_APP_SETTING_USB_STREAMING_PROCAM", msg=body)
            if body == p285.BODY_MODEL_FX6:
                self.assertEqual(r.menu_path, p285.FX6_USB_PROCAM_UVC_MENU_PATH)

    def test_19_sibling_uvc_also_blocked_if_tier0_unisolated_eacces(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            body_profile=p285.BODY_MODEL_FX6,
            requested_usb_connection_mode=p285.USB_MODE_DORMANT_STREAMING,
            usb_port=p285.USB_PORT_TYPE_C,
            tier0_airgapped_bench=True,
            usb_data_lines_physically_isolated=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EACCES_ERRNO)
        self.assertEqual(r.tier0_usb_data_enumeration_violations, 0)

    def test_20_usb_lun_setting_multi_2luns_vs_single_1lun_in_msc(self) -> None:
        r_multi = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            requested_usb_connection_mode=p285.USB_MODE_MASS_STORAGE,
            configured_usb_lun_setting=p285.USB_LUN_MULTI,
            usb_port=p285.USB_PORT_TYPE_C,
            tier0_airgapped_bench=False,
        )
        r_single = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            requested_usb_connection_mode=p285.USB_MODE_MASS_STORAGE,
            configured_usb_lun_setting=p285.USB_LUN_SINGLE,
            usb_port=p285.USB_PORT_TYPE_C,
            tier0_airgapped_bench=False,
        )
        self.assertTrue(r_multi.admitted)
        self.assertEqual(r_multi.exposed_msc_luns, 2)
        self.assertEqual(r_multi.effective_usb_vid_pid, "054C:0DA1")
        self.assertTrue(r_single.admitted)
        self.assertEqual(r_single.exposed_msc_luns, 1)
        self.assertEqual(p285.USB_LUN_SPEC["Multi"]["resid16"], "0xe631")
        self.assertEqual(p285.USB_LUN_SPEC["Single"]["resid16"], "0x776d")

    def test_21_non_msc_modes_expose_zero_msc_luns(self) -> None:
        for mode in (
            p285.USB_MODE_SEL_WHEN_CONNECT,
            p285.USB_MODE_MTP,
            p285.USB_MODE_REMOTE_SHOOT,
        ):
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
                requested_usb_connection_mode=mode,
                tier0_airgapped_bench=False,
            )
            self.assertTrue(r.admitted, msg=mode)
            self.assertEqual(r.exposed_msc_luns, 0, msg=mode)

    def test_22_tier0_airgapped_bench_admits_usb_pd_only_when_data_lines_isolated(self) -> None:
        r_ok = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            body_profile=p285.BODY_MODEL_FX3,
            requested_usb_connection_mode=p285.USB_MODE_SEL_WHEN_CONNECT,
            configured_usb_power_supply=p285.TOGGLE_ON,
            usb_port=p285.USB_PORT_TYPE_C,
            np_fz100_inserted=True,
            usb_pd_watts=27.0,
            tier0_airgapped_bench=True,
            usb_data_lines_physically_isolated=True,
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.usb_power_supply_active)
        self.assertTrue(r_ok.data_isolated_pd_admitted)
        self.assertEqual(r_ok.physical_usb_packets_emitted, 0)
        self.assertEqual(r_ok.tier0_usb_data_enumeration_violations, 0)

    def test_23_tier0_airgapped_bench_blocks_unisolated_usb_data_lines_eacces(self) -> None:
        for mode in p285.FX3_EXPOSED_USB_CONNECTION_MODES:
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
                body_profile=p285.BODY_MODEL_FX3,
                requested_usb_connection_mode=mode,
                usb_port=p285.USB_PORT_TYPE_C,
                np_fz100_inserted=True,
                usb_pd_watts=27.0,
                tier0_airgapped_bench=True,
                usb_data_lines_physically_isolated=False,
            )
            self.assertFalse(r.admitted, msg=mode)
            self.assertEqual(r.errno_code, p285.EACCES_ERRNO, msg=mode)
            self.assertEqual(r.reason_code, "TIER0_BENCH_USB_DATA_ENUMERATION_BLOCKED", msg=mode)
            self.assertFalse(r.data_isolated_pd_admitted, msg=mode)

    def test_24_usb_power_supply_off_disables_pd_charging_even_on_type_c(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            configured_usb_power_supply=p285.TOGGLE_OFF,
            usb_port=p285.USB_PORT_TYPE_C,
            np_fz100_inserted=True,
            usb_pd_watts=27.0,
            tier0_airgapped_bench=True,
            usb_data_lines_physically_isolated=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.usb_power_supply_active)
        self.assertFalse(r.data_isolated_pd_admitted)

    def test_25_multi_micro_usb_port_rejects_usb_pd_power_supply_eopnotsupp(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            usb_port=p285.USB_PORT_MULTI_MICRO,
            usb_pd_watts=10.0,
            tier0_airgapped_bench=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "USB_POWER_SUPPLY_REQUIRES_TYPE_C_PORT")

    def test_26_usb_power_supply_without_np_fz100_battery_rejected_eacces(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            usb_port=p285.USB_PORT_TYPE_C,
            np_fz100_inserted=False,
            usb_pd_watts=27.0,
            force_usb_power_without_battery=True,
            tier0_airgapped_bench=True,
            usb_data_lines_physically_isolated=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EACCES_ERRNO)
        self.assertEqual(r.reason_code, "USB_POWER_SUPPLY_REQUIRES_NP_FZ100_BATTERY")

    def test_27_usb_setup_items_survive_camera_settings_reset_and_network_reset(self) -> None:
        for act in (
            p285.RESET_ACTION_CAMERA_SETTINGS_RESET,
            p285.RESET_ACTION_RESET_NETWORK_SET,
        ):
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
                requested_usb_connection_mode=p285.USB_MODE_REMOTE_SHOOT,
                configured_usb_lun_setting=p285.USB_LUN_SINGLE,
                configured_usb_power_supply=p285.TOGGLE_OFF,
                tier0_airgapped_bench=False,
                reset_action=act,
            )
            self.assertTrue(r.admitted, msg=act)
            self.assertTrue(r.setup_usb_items_survived_camera_reset, msg=act)
            self.assertFalse(r.setup_usb_items_restored_by_initialize, msg=act)
            self.assertEqual(r.effective_usb_connection_mode, "Remote Shoot (PC Remote)")
            self.assertEqual(r.effective_usb_lun_setting, "Single")
            self.assertEqual(r.effective_usb_power_supply, "Off")

    def test_28_initialize_restores_all_3_usb_setup_items_to_factory_defaults(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            requested_usb_connection_mode=p285.USB_MODE_MASS_STORAGE,
            configured_usb_lun_setting=p285.USB_LUN_SINGLE,
            configured_usb_power_supply=p285.TOGGLE_OFF,
            tier0_airgapped_bench=False,
            reset_action=p285.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.setup_usb_items_restored_by_initialize)
        self.assertFalse(r.setup_usb_items_survived_camera_reset)
        self.assertEqual(r.effective_usb_connection_mode, "Sel. When Connect")
        self.assertEqual(r.effective_usb_lun_setting, "Multi")
        self.assertEqual(r.effective_usb_power_supply, "On")

    def test_29_invalid_usb_mode_lun_supply_port_watts_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"requested_usb_connection_mode": "PTP/IP_DIRECT"},
            {"configured_usb_lun_setting": "Triple"},
            {"configured_usb_power_supply": "Auto"},
            {"usb_port": "LIGHTNING"},
            {"usb_pd_watts": -1.0},
            {"usb_pd_watts": 150.0},
            {"usb_pd_watts": True},
            {"reset_action": "UNKNOWN"},
        ):
            r = p285.simulate_usb_connection_mode_nouvc_pd_hil(**kwargs)  # type: ignore[arg-type]
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p285.EINVAL_ERRNO, msg=str(kwargs))

    def test_30_pillar_a_passed_and_4mode_matrix_complete(self) -> None:
        pa = self.clean_audit["pillar_a_usb_connection_mode_nouvc_pd_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["fx3_4mode_matrix"]), 4)
        self.assertEqual(set(pa["fx3_4mode_matrix"].keys()), set(p285.FX3_EXPOSED_USB_CONNECTION_MODES))

    def test_31_all_usb_simulations_perform_zero_physical_or_nvram_writes(self) -> None:
        pa = self.default_audit["pillar_a_usb_connection_mode_nouvc_pd_hil"]
        for entry in pa["fx3_4mode_matrix"].values():
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(entry["physical_usb_packets_emitted"], 0)

    def test_32_usb_power_zero_watts_with_type_c_keeps_supply_inactive(self) -> None:
        r = p285.simulate_usb_connection_mode_nouvc_pd_hil(
            usb_port=p285.USB_PORT_TYPE_C,
            np_fz100_inserted=True,
            usb_pd_watts=0.0,
            tier0_airgapped_bench=True,
            usb_data_lines_physically_isolated=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.usb_power_supply_active)
        self.assertFalse(r.data_isolated_pd_admitted)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 57B — [HDMI Info. Display] LCD-Blanking vs
    #          Clean-Feed, 1080 Clamp & 4K Override (18 tests)
    # ------------------------------------------------------------------
    def test_33_hdmi_info_display_default_on_emits_osd_and_blanks_lcd_touch_focus(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.menu_path, p285.HDMI_INFO_DISPLAY_MENU_PATH)
        self.assertEqual(r.effective_hdmi_info_display, "On")
        self.assertTrue(r.hdmi_osd_overlays_emitted)
        self.assertTrue(r.hdmi_letterbox_inset_active)
        self.assertFalse(r.builtin_lcd_active)
        self.assertFalse(r.lcd_touch_focus_enabled)
        self.assertFalse(r.auto_clean_feed_forced_off)

    def test_34_hdmi_info_display_off_outputs_clean_feed_and_keeps_lcd_active(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_OFF,
            configured_output_resolution=p285.HDMI_RES_2160P,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertFalse(r.hdmi_osd_overlays_emitted)
        self.assertFalse(r.hdmi_letterbox_inset_active)
        self.assertTrue(r.builtin_lcd_active)
        self.assertTrue(r.lcd_touch_focus_enabled)
        self.assertEqual(r.effective_hdmi_width, 3840)
        self.assertEqual(r.effective_hdmi_height, 2160)

    def test_35_internal_rec_plus_all_3_log_shooting_modes_clamp_hdmi_to_1080(self) -> None:
        for log_mode in (
            p285.LOG_SHOOTING_FLEXIBLE_ISO,
            p285.LOG_SHOOTING_CINE_EI,
            p285.LOG_SHOOTING_CINE_EI_QUICK,
        ):
            r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
                configured_hdmi_info_display=p285.TOGGLE_OFF,
                configured_output_resolution=p285.HDMI_RES_2160P,
                configured_rec_media_during_hdmi=p285.REC_MEDIA_ON,
                configured_log_shooting=log_mode,
            )
            self.assertTrue(r.admitted, msg=log_mode)
            self.assertTrue(r.hdmi_1080_log_pplut_clamped, msg=log_mode)
            self.assertEqual(r.effective_hdmi_width, 1920, msg=log_mode)
            self.assertEqual(r.effective_hdmi_height, 1080, msg=log_mode)

    def test_36_internal_rec_plus_pplut1_to_4_clamps_hdmi_to_1080(self) -> None:
        for pplut in p285.PICTURE_PROFILE_PPLUT_MODES:
            r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
                configured_output_resolution=p285.HDMI_RES_2160P,
                configured_rec_media_during_hdmi=p285.REC_MEDIA_ON,
                configured_picture_profile=pplut,
            )
            self.assertTrue(r.admitted, msg=pplut)
            self.assertTrue(r.hdmi_1080_log_pplut_clamped, msg=pplut)
            self.assertEqual(r.effective_hdmi_width, 1920, msg=pplut)
            self.assertEqual(r.effective_hdmi_height, 1080, msg=pplut)

    def test_37_pp11_without_log_does_not_trigger_pplut_1080_clamp(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_output_resolution=p285.HDMI_RES_2160P,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_ON,
            configured_picture_profile=p285.PICTURE_PROFILE_PP11,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.hdmi_1080_log_pplut_clamped)
        self.assertEqual(r.effective_hdmi_width, 3840)

    def test_38_log_pplut_1080i_resolution_honored_under_clamp(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_output_resolution=p285.HDMI_RES_1080I,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_ON,
            configured_log_shooting=p285.LOG_SHOOTING_CINE_EI,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.hdmi_1080_log_pplut_clamped)
        self.assertIn("1080i", r.effective_hdmi_output_label)

    def test_39_forced_4k_bypass_during_internal_log_or_pplut_rejected_eopnotsupp(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_output_resolution=p285.HDMI_RES_2160P,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_ON,
            configured_log_shooting=p285.LOG_SHOOTING_CINE_EI,
            force_4k_during_internal_log_or_pplut=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "INTERNAL_REC_LOG_PPLUT_CLAMPED_TO_1080")
        self.assertEqual(r.hdmi_osd_or_clamp_bypass_events, 0)

    def test_40_rec_media_off_hdmi_only_outputs_4k_and_auto_forces_hdmi_info_off(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_ON,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_OFF_HDMI_ONLY,
            configured_log_shooting=p285.LOG_SHOOTING_CINE_EI,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_clean_feed_forced_off)
        self.assertFalse(r.hdmi_1080_log_pplut_clamped)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertFalse(r.hdmi_osd_overlays_emitted)
        self.assertTrue(r.builtin_lcd_active)
        self.assertEqual(r.effective_hdmi_width, 3840)
        self.assertEqual(r.effective_hdmi_height, 2160)

    def test_41_raw_output_on_outputs_4264x2408_4k_and_auto_forces_hdmi_info_off(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_ON,
            configured_raw_output=p285.TOGGLE_ON,
            configured_log_shooting=p285.LOG_SHOOTING_FLEXIBLE_ISO,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_clean_feed_forced_off)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertFalse(r.hdmi_osd_overlays_emitted)
        self.assertTrue(r.builtin_lcd_active)
        self.assertEqual(r.effective_hdmi_width, 4264)
        self.assertEqual(r.effective_hdmi_height, 2408)

    def test_42_forced_osd_during_raw_or_hdmi_only_rejected_eopnotsupp(self) -> None:
        for kwargs in (
            {"configured_raw_output": p285.TOGGLE_ON},
            {"configured_rec_media_during_hdmi": p285.REC_MEDIA_OFF_HDMI_ONLY},
        ):
            r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
                configured_hdmi_info_display=p285.TOGGLE_ON,
                force_osd_during_raw_or_hdmi_only=True,
                **kwargs,
            )
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p285.EOPNOTSUPP_ERRNO, msg=str(kwargs))
            self.assertEqual(r.reason_code, "RAW_OR_HDMI_ONLY_FORCES_CLEAN_FEED_OFF")
            self.assertEqual(r.hdmi_clean_feed_override_violations, 0)

    def test_43_sq_mode_locks_rec_media_on_and_raw_output_off_eopnotsupp(self) -> None:
        for kwargs in (
            {"configured_raw_output": p285.TOGGLE_ON},
            {"configured_rec_media_during_hdmi": p285.REC_MEDIA_OFF_HDMI_ONLY},
        ):
            r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
                shoot_mode=p285.SHOOT_MODE_SQ,
                **kwargs,
            )
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p285.EOPNOTSUPP_ERRNO, msg=str(kwargs))
            self.assertEqual(r.reason_code, "SQ_MODE_LOCKS_REC_MEDIA_ON_AND_RAW_OFF")

    def test_44_camera_settings_reset_preserves_hdmi_info_and_rec_media_resets_framing(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_OFF,
            configured_output_resolution=p285.HDMI_RES_1080P,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_OFF_HDMI_ONLY,
            configured_framing_settings_hdmi="Crop",
            reset_action=p285.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.setup_hdmi_items_survived_camera_reset)
        self.assertTrue(r.framing_settings_hdmi_reset_by_camera_reset)
        self.assertFalse(r.setup_hdmi_restored_by_initialize)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertTrue(r.auto_clean_feed_forced_off)
        self.assertEqual(r.effective_framing_settings_hdmi, "Full")

    def test_45_reset_network_set_preserves_hdmi_info_and_framing(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_OFF,
            configured_framing_settings_hdmi="Crop",
            reset_action=p285.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.setup_hdmi_items_survived_camera_reset)
        self.assertFalse(r.framing_settings_hdmi_reset_by_camera_reset)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertEqual(r.effective_framing_settings_hdmi, "Crop")

    def test_46_initialize_restores_all_hdmi_items_to_factory_defaults(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            configured_hdmi_info_display=p285.TOGGLE_OFF,
            configured_output_resolution=p285.HDMI_RES_1080P,
            configured_rec_media_during_hdmi=p285.REC_MEDIA_OFF_HDMI_ONLY,
            configured_raw_output=p285.TOGGLE_ON,
            configured_framing_settings_hdmi="Crop",
            reset_action=p285.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.setup_hdmi_restored_by_initialize)
        self.assertEqual(r.effective_hdmi_info_display, "On")
        self.assertFalse(r.auto_clean_feed_forced_off)
        self.assertEqual(r.effective_framing_settings_hdmi, "Full")

    def test_47_fx6_hdmi_output_display_vs_sdi_menu_path_parity(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            body_profile=p285.BODY_MODEL_FX6,
            configured_hdmi_info_display=p285.TOGGLE_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.menu_path, p285.FX6_HDMI_INFO_DISPLAY_MENU_PATH)
        self.assertFalse(r.hdmi_osd_overlays_emitted)
        self.assertTrue(r.builtin_lcd_active)

    def test_48_invalid_hdmi_parameters_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"shoot_mode": "3D_VR"},
            {"configured_hdmi_info_display": "Partial"},
            {"configured_output_resolution": "4320p"},
            {"configured_rec_media_during_hdmi": "Dual"},
            {"configured_log_shooting": "S-Log2"},
            {"configured_picture_profile": "PP99"},
            {"configured_raw_output": "12bit"},
            {"configured_framing_settings_hdmi": "PanScan"},
            {"reset_action": "UNKNOWN"},
        ):
            r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p285.EINVAL_ERRNO, msg=str(kwargs))

    def test_49_pillar_b_passed_flag_and_zero_override_violations(self) -> None:
        pb = self.clean_audit["pillar_b_hdmi_info_display_cleanfeed_override_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["menu_path"], p285.HDMI_INFO_DISPLAY_MENU_PATH)
        self.assertEqual(pb["log_shooting_1080_clamped"]["effective_hdmi_height"], 1080)
        self.assertEqual(pb["raw_4k_forced_clean_feed"]["effective_hdmi_width"], 4264)

    def test_50_still_mode_hdmi_info_display_auto_2160p_clean_feed_behavior(self) -> None:
        r = p285.simulate_hdmi_info_display_cleanfeed_override_hil(
            shoot_mode=p285.SHOOT_MODE_STILL,
            configured_hdmi_info_display=p285.TOGGLE_OFF,
            configured_output_resolution=p285.HDMI_RES_AUTO,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.hdmi_osd_overlays_emitted)
        self.assertTrue(r.builtin_lcd_active)
        self.assertEqual(r.effective_hdmi_width, 3840)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 57C — [Protect] 4-Scopes vs [Format] Wipe
    #          (Slot-1 Dual-Layer SD WP) & [Reset Network Set.] HIL (18 tests)
    # ------------------------------------------------------------------
    def test_51_fx3_protect_exact_4_scopes_and_resid16_contracts(self) -> None:
        self.assertEqual(len(p285.ALL_4_PROTECT_SCOPES), 4)
        self.assertEqual(
            p285.ALL_4_PROTECT_SCOPES,
            (
                "Multiple Img.",
                "All in this Folder",
                "All with this date",
                "All Images in This Group",
            ),
        )
        self.assertEqual(p285.PROTECT_SCOPE_SPEC["Multiple Img."]["resid16"], "0xe2ca")
        self.assertEqual(p285.PROTECT_SCOPE_SPEC["All in this Folder"]["resid16"], "0x6848")
        self.assertEqual(p285.PROTECT_SCOPE_SPEC["All with this date"]["resid16"], "0x69f7")
        self.assertEqual(p285.PROTECT_SCOPE_SPEC["All Images in This Group"]["resid16"], "0xe826")

    def test_52_all_4_protect_scopes_block_delete_and_delete_twice_erofs(self) -> None:
        for scope in p285.ALL_4_PROTECT_SCOPES:
            for del_op in (p285.MEDIA_OP_DELETE_SINGLE, p285.MEDIA_OP_DELETE_TWICE):
                r = p285.simulate_protect_format_network_reset_hil(
                    target_slot=p285.SLOT_2,
                    protect_scope=scope,
                    protected_files_active=True,
                    requested_media_op=del_op,
                )
                self.assertFalse(r.admitted, msg=f"{scope}:{del_op}")
                self.assertEqual(r.errno_code, p285.EROFS_ERRNO, msg=f"{scope}:{del_op}")
                self.assertTrue(r.delete_blocked_by_protect, msg=f"{scope}:{del_op}")
                self.assertFalse(r.media_op_executed, msg=f"{scope}:{del_op}")

    def test_53_unprotected_files_on_slot2_allow_delete_with_zero_physical_writes(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            target_slot=p285.SLOT_2,
            protect_scope=p285.PROTECT_SCOPE_NONE,
            protected_files_active=False,
            requested_media_op=p285.MEDIA_OP_DELETE_SINGLE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.media_op_executed)
        self.assertEqual(r.physical_device_writes, 0)

    def test_54_format_quick_and_full_on_slot2_wipe_protected_files_and_m1_m4(self) -> None:
        for fmt_op in (p285.MEDIA_OP_FORMAT_QUICK, p285.MEDIA_OP_FORMAT_FULL):
            r = p285.simulate_protect_format_network_reset_hil(
                target_slot=p285.SLOT_2,
                protect_scope=p285.PROTECT_SCOPE_ALL_IN_GROUP,
                protected_files_active=True,
                requested_media_op=fmt_op,
            )
            self.assertTrue(r.admitted, msg=fmt_op)
            self.assertTrue(r.media_op_executed, msg=fmt_op)
            self.assertTrue(r.format_wiped_protected_files_and_m1_m4, msg=fmt_op)
            self.assertFalse(r.camset_m1_m4_intact, msg=fmt_op)
            self.assertFalse(r.protected_files_active, msg=fmt_op)
            self.assertFalse(r.camset_slot_files_preserved, msg=fmt_op)
            self.assertEqual(r.physical_device_writes, 0, msg=fmt_op)

    def test_55_slot1_dual_layer_sd_wp_plus_firewall_blocks_format_and_delete_erofs(self) -> None:
        for wp_locked in (True, False):
            for op in (
                p285.MEDIA_OP_DELETE_SINGLE,
                p285.MEDIA_OP_DELETE_TWICE,
                p285.MEDIA_OP_FORMAT_QUICK,
                p285.MEDIA_OP_FORMAT_FULL,
            ):
                r = p285.simulate_protect_format_network_reset_hil(
                    target_slot=p285.SLOT_1,
                    slot1_holds_recovery_vault=True,
                    slot1_sd_hw_wp_switch_locked=wp_locked,
                    requested_media_op=op,
                )
                self.assertFalse(r.admitted, msg=f"wp={wp_locked}:{op}")
                self.assertEqual(r.errno_code, p285.EROFS_ERRNO)
                self.assertTrue(r.slot1_format_hard_locked)
                self.assertFalse(r.media_op_executed)
                self.assertEqual(r.slot1_vault_format_or_delete_events, 0)
                if wp_locked:
                    self.assertEqual(
                        r.reason_code, "SLOT1_DUAL_LAYER_SD_WP_AND_FORMAT_FIREWALL_BLOCKED"
                    )
                else:
                    self.assertEqual(r.reason_code, "SLOT1_FORMAT_FIREWALL_BLOCKED")

    def test_56_reset_network_set_clears_network_preserves_shooting_setup_playback_camset(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            target_slot=p285.SLOT_1,
            reset_action=p285.RESET_ACTION_RESET_NETWORK_SET,
            post_reboot_airplane_mode=p285.TOGGLE_ON,
            zero_rf_bench_requires_airplane_on=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.network_credentials_cleared)
        self.assertTrue(r.shooting_setup_playback_preserved)
        self.assertTrue(r.camset_slot_files_preserved)
        self.assertTrue(r.camset_m1_m4_intact)
        self.assertTrue(r.auto_reboot_triggered)
        self.assertEqual(r.shutdown_factor_bkid, "BKID_APP_is_shutdown_factor_network_reset")
        self.assertEqual(r.post_reset_airplane_mode_default, "Off")
        self.assertEqual(r.post_reboot_airplane_mode, "On")
        self.assertTrue(r.zero_rf_posture_restored)
        self.assertEqual(r.post_reset_airplane_off_rf_leak_events, 0)
        self.assertEqual(r.passive_tx_bytes_emitted, 0)

    def test_57_reset_network_set_leaves_airplane_off_and_fails_zero_rf_guard_eacces(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            target_slot=p285.SLOT_1,
            reset_action=p285.RESET_ACTION_RESET_NETWORK_SET,
            post_reboot_airplane_mode=p285.TOGGLE_OFF,
            zero_rf_bench_requires_airplane_on=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EACCES_ERRNO)
        self.assertEqual(r.reason_code, "POST_NETWORK_RESET_REQUIRES_AIRPLANE_MODE_ON")
        self.assertTrue(r.network_credentials_cleared)
        self.assertTrue(r.auto_reboot_triggered)
        self.assertEqual(r.post_reset_airplane_mode_default, "Off")
        self.assertFalse(r.zero_rf_posture_restored)
        self.assertEqual(r.post_reset_airplane_off_rf_leak_events, 0)

    def test_58_non_reset_with_airplane_off_on_zero_rf_bench_blocked_eacces(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            reset_action=p285.RESET_ACTION_NONE,
            post_reboot_airplane_mode=p285.TOGGLE_OFF,
            zero_rf_bench_requires_airplane_on=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p285.EACCES_ERRNO)
        self.assertEqual(r.reason_code, "ZERO_RF_BENCH_REQUIRES_AIRPLANE_MODE_ON")

    def test_59_fx6_network_reset_shutdown_factor_parity(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            body_profile=p285.BODY_MODEL_FX6,
            target_slot=p285.SLOT_2,
            reset_action=p285.RESET_ACTION_RESET_NETWORK_SET,
            post_reboot_airplane_mode=p285.TOGGLE_ON,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.shutdown_factor_bkid, "BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET")
        self.assertTrue(r.auto_reboot_triggered)
        self.assertTrue(r.zero_rf_posture_restored)

    def test_60_network_credentials_domains_cover_all_12_domains(self) -> None:
        self.assertEqual(len(p285.NETWORK_CREDENTIALS_DOMAINS), 12)
        for required in (
            "wifi_ssid_psk",
            "bluetooth_pairing",
            "ftp_profiles_0_to_8",
            "creators_cloud",
            "root_certificates",
        ):
            self.assertIn(required, p285.NETWORK_CREDENTIALS_DOMAINS)

    def test_61_invalid_protect_format_network_reset_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"target_slot": "Slot 3"},
            {"protect_scope": "All in Camera"},
            {"requested_media_op": "LowLevelErase"},
            {"reset_action": "UNKNOWN"},
            {"post_reboot_airplane_mode": "Auto"},
        ):
            r = p285.simulate_protect_format_network_reset_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p285.EINVAL_ERRNO, msg=str(kwargs))

    def test_62_pillar_cd_passed_and_covers_all_4_protect_and_slot1_ops(self) -> None:
        pcd = self.clean_audit["pillar_c_d_protect_format_network_reset_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["protect_4scope_blocks_delete"]), 4)
        self.assertEqual(len(pcd["slot1_vault_dual_layer_blocked_erofs"]), 4)
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])

    def test_63_donor_appfw_protect_and_network_reset_tokens_verified(self) -> None:
        da = self.default_audit["donor_audit"]
        for tok in (
            "FUNC_PROTECT_CONTENT",
            "FUNC_PROTECT_DATE",
            "FUNC_PROTECT_GROUP",
            "FUNC_PROTECT_MULTI",
            "FUNC_RESET_NETWORK",
            "FUNC_RESET_WIFI_PSK",
            "MR_ERR_CARD_WP_SLOT1",
            "MR_ERR_FILE_PROTECT",
            "CAUTION_PROTECT_SLOT1",
            "BKID_AIRPLANE_MODE",
            "BKID_SHUTDOWN_NET_RESET",
        ):
            self.assertEqual(da["fx3_appfw"]["window_hits"][tok], 1, msg=tok)

    def test_64_fx6_donor_lock_clip_and_network_reset_tokens_verified(self) -> None:
        da = self.default_audit["donor_audit"]
        for tok in ("FX6_LOCK_CLIP0", "FX6_NET_RESET_MENU", "FX6_SHUTDOWN_NET_RESET"):
            self.assertEqual(da["fx6_appfw"]["window_hits"][tok], 1, msg=tok)

    def test_65_protect_format_zero_physical_and_bk4_writes_in_all_cases(self) -> None:
        pcd = self.default_audit["pillar_c_d_protect_format_network_reset_and_redlines"]
        for entry in pcd["protect_4scope_blocks_delete"].values():
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["bk4_persistent_nvram_writes"], 0)
        for entry in pcd["slot1_vault_dual_layer_blocked_erofs"].values():
            self.assertEqual(entry["physical_device_writes"], 0)
            self.assertEqual(entry["slot1_vault_format_or_delete_events"], 0)

    def test_66_camera_settings_reset_does_not_clear_network_or_reboot(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            reset_action=p285.RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reboot_airplane_mode=p285.TOGGLE_ON,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.network_credentials_cleared)
        self.assertFalse(r.auto_reboot_triggered)

    def test_67_initialize_clears_network_and_preserves_slot1_vault(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            target_slot=p285.SLOT_1,
            reset_action=p285.RESET_ACTION_INITIALIZE,
            post_reboot_airplane_mode=p285.TOGGLE_ON,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.network_credentials_cleared)
        self.assertTrue(r.camset_slot_files_preserved)
        self.assertTrue(r.slot1_format_hard_locked)

    def test_68_non_zero_rf_lab_override_allows_airplane_off_reporting_when_flagged(self) -> None:
        r = p285.simulate_protect_format_network_reset_hil(
            reset_action=p285.RESET_ACTION_RESET_NETWORK_SET,
            post_reboot_airplane_mode=p285.TOGGLE_OFF,
            zero_rf_bench_requires_airplane_on=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.zero_rf_posture_restored)
        self.assertEqual(r.post_reset_airplane_mode_default, "Off")

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 57 (57/57) Suite & Subprocess
    #          Portability Hygiene (8 tests -> Total 76)
    # ------------------------------------------------------------------
    def test_69_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p285.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p285.probe_phase285_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p285.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p285.probe_phase285_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.slot1_vault_format_or_delete_events, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p285.probe_phase285_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p285.EINVAL_ERRNO)

    def test_70_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p285.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 285 Stage 57 (57/57)", proc_sum.stdout)
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
        self.assertEqual(data["milestone"], "57/57")
        self.assertEqual(data["phase_number"], 285)

    def test_71_suite_stage57_57_of_57_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s57 = rep["stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil"]
            self.assertTrue(s57["all_checks_passed"])
            self.assertEqual(s57["phase_number"], 285)
            self.assertEqual(s57["milestone"], "57/57")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 57)

    def test_72_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 15.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_73_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_74_suite_stage57_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil
        )
        self.assertTrue(default_cfg.include_stage57)
        self.assertTrue(
            default_cfg.include_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil
        )

        for override in (
            {"stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil": False},
            {"include_stage57": False},
            {"include_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage57"])
            self.assertFalse(
                rep["config"]["stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil"]
            )

    def test_75_fx3_vm_coemulation_suite_include_stage57_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage57", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_usb_mode_hdmi_info_protect_network_reset_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_76_fx3_vm_coemulation_suite_cli_skip_phase285_and_skip_stage57(self) -> None:
        for skip_flag in ("--skip-phase285", "--skip-stage57", "--no-include-stage57"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil", parsed
            )


if __name__ == "__main__":
    unittest.main()
