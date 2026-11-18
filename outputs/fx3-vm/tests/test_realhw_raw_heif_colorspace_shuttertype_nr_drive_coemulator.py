#!/usr/bin/env python3
"""Unit tests for Phase 293 (Stage 59, 59/59):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-49
Still `[Image Quality Settings]` (`RAW` `Compressed`/`Uncompressed` vs Dormant `Lossless Comp`,
`JPEG/HEIF Switch` `JPEG / HEIF(4:2:0) / HEIF(4:2:2)` 10-bit `.HIF`, & `[HLG Still Image]`
`BT.2100` Override vs Still-Less `ILME-FX6`),
`[Color Space]` (`sRGB` Default vs `AdobeRGB` `_DSC` Prefix) & `[Set File Name]` Leading-`_` Ban,
and `[Shutter Type]` Exact 2-Option Split (`Mechanical Shutter` Default vs `Electronic Shutter`
— NO `Auto`!), Electronic/Silent 5-Lock Matrix, `[Long Exposure NR]` / `[High ISO NR]`, &
`[Drive Mode]` `10 fps` `Slot-1` Tier-0 Vault Firewall HIL Co-Emulator (78 dual-mode tests).
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
import realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator as p293  # noqa: E402

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
        include_stage57=False,
        include_stage58=False,
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
]


class TestPhase293Stage59Wave49HilCoEmulator(unittest.TestCase):
    """78 dual-mode tests for Phase 293 Stage 59 (59/59)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.default_audit = p293.run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil()
        cls.clean_audit = p293.run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil(
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
    # Group 1: Schema, Redlines & Dual-Mode 11-Donor O_RDONLY Audit (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_phase_and_milestone_constants(self) -> None:
        self.assertEqual(p293.SCHEMA_ID, "realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator_v1")
        self.assertEqual(p293.PHASE_293_SCHEMA, p293.SCHEMA_ID)
        self.assertEqual(p293.PHASE_293_VERSION, "293.0.0")
        self.assertEqual(p293.PHASE_NUMBER, 293)
        self.assertEqual(p293.STAGE_INDEX, 59)
        self.assertEqual(p293.STAGE_TOTAL, 59)
        self.assertEqual(p293.MILESTONE_LABEL, "59/59")
        self.assertEqual(
            p293.STAGE_NAME, "stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil"
        )
        self.assertEqual(p293.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p293.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p293.FX3_HELP_GUIDE_ID, "ilc/2210")

    def test_02_hard_safety_redline_constants_locked(self) -> None:
        self.assertTrue(p293.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p293.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(p293.FX3_MECHANICAL_SHUTTER_PRESENT)
        self.assertFalse(p293.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p293.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p293.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p293.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p293.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p293.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p293.FX6_STILL_PIPELINE_EXPOSED)
        self.assertFalse(p293.FX6_MECHANICAL_SHUTTER_PRESENT)
        for zero_val in (
            p293.NOP_COUNT,
            p293.GUEST_CODE_MODIFICATION_BYTES,
            p293.CP_MUTATION_BYTES,
            p293.WBI_MUTATION_BYTES,
            p293.CALIBRATION_MUTATION_BYTES,
            p293.CNFLASHA_MUTATION_BYTES,
            p293.NVRAM_PERSISTENT_WRITES,
            p293.BK4_PERSISTENT_NVRAM_WRITES,
            p293.PHYSICAL_DEVICE_WRITES,
            p293.EMMC_NFLASHA_WRITE_COUNT,
            p293.EMMC_MUTATION_BYTES,
            p293.EMMC_CORRUPTIONS,
            p293.SPI_NOR_MUTATION_BYTES,
            p293.OTP_FUSE_TOUCHES,
            p293.RPMB_COUNTER_INCREMENTS,
            p293.PHYSICAL_USB_PACKETS_EMITTED,
            p293.PASSIVE_TX_BYTES_EMITTED,
            p293.DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
            p293.HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
            p293.COLOR_SPACE_LEADING_UNDERSCORE_BYPASS_EVENTS,
            p293.SHUTTER_TYPE_AUTO_OR_5LOCK_BYPASS_EVENTS,
            p293.SLOT1_VAULT_STILL_OR_BURST_WRITE_EVENTS,
            p293.RSV_ORPHAN_COUNT,
            p293.WF12_00342260_HITS,
            p293.APPFW_CRASHES,
            p293.NULL_GPIO_DEREFS,
            p293.MAILBOX_STALLS,
            p293.STOCK_CP_FAULT_COUNT,
            p293.RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_val, 0)

    def test_03_default_and_clean_room_reports_both_pass(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p293.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(self.default_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.clean_audit["donor_audit"]["donor_files_inspected"], 11)
        self.assertEqual(self.default_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(self.clean_audit["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_04_is_forced_clean_room_both_env_vars(self) -> None:
        self.assertFalse(p293.is_forced_clean_room({}))
        self.assertTrue(p293.is_forced_clean_room({p293.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p293.is_forced_clean_room({p293.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertTrue(p293.is_forced_clean_room({p293.ENV_FORCE_CLEAN_ROOM: "YES"}))
        self.assertFalse(p293.is_forced_clean_room({p293.ENV_CLEAN_ROOM_TEST: "0"}))

    def test_05_all_11_donors_verified_in_donor_audit(self) -> None:
        da = self.default_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        self.assertTrue(da["raw_heif_hlg_proven"])
        self.assertTrue(da["colorspace_setfilename_proven"])
        self.assertTrue(da["shuttertype_nr_drive_proven"])
        self.assertEqual(da["errors"], ())
        self.assertEqual(len(p293.DONOR_RELPATHS), 11)
        self.assertEqual(len(p293.EXPECTED_DONOR_BYTES), 11)

    def test_06_clean_room_11_donors_synthetic_parity(self) -> None:
        da = self.clean_audit["donor_audit"]
        self.assertEqual(da["source_mode"], p293.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(da["access_mode"], p293.DONOR_ACCESS_MODE)
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["fx3_appfw"]["file_bytes"], p293.EXPECTED_DONOR_BYTES["fx3_appfw"])
        self.assertEqual(da["fx3_bk4"]["file_bytes"], p293.EXPECTED_DONOR_BYTES["fx3_bk4"])
        self.assertEqual(da["fx6_appfw"]["file_bytes"], p293.EXPECTED_DONOR_BYTES["fx6_appfw"])
        self.assertTrue(da["fx3_appfw"]["bounded_windows_only"])

    def test_07_bounded_windows_never_exceed_4096_bytes_and_o_rdonly(self) -> None:
        self.assertLessEqual(p293.BOUNDED_WINDOW_MAX_BYTES, 4096)
        for key, windows in p293.LARGE_DONOR_WINDOWS.items():
            offsets = sorted({w[0] for w in windows})
            self.assertGreaterEqual(len(offsets), 2, msg=key)
            self.assertEqual(
                self.clean_audit["donor_audit"][key]["bytes_read_total"],
                len(offsets) * p293.BOUNDED_WINDOW_MAX_BYTES,
                msg=key,
            )

    def test_08_missing_mac_root_falls_back_to_clean_room_without_error(self) -> None:
        with unittest.mock.patch.object(
            p293,
            "_iter_work_roots",
            return_value=(Path("/nonexistent/phase293/missing_work"),),
        ):
            missing = p293.inspect_phase293_donors()
        self.assertEqual(missing.source_mode, p293.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(missing.all_contracts_verified)
        self.assertEqual(missing.raw_firmware_bytes_leaked, 0)

    def test_09_donor_audit_cold_perf_under_budget(self) -> None:
        p293._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        audit = p293.inspect_phase293_donors(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(audit.all_contracts_verified)
        self.assertLess(elapsed, 15.0 if IS_CI else 0.5)

    def test_10_clean_room_payload_digest_deterministic(self) -> None:
        a = p293.run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil(
            force_clean_room=True
        )
        b = p293.run_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil(
            force_clean_room=True
        )
        self.assertEqual(a["audit_digest_sha256"], b["audit_digest_sha256"])

    def test_11_uxc_and_appfw_exact_sha256_constants_present(self) -> None:
        self.assertEqual(len(p293.EXPECTED_COMPACT_DONOR_SHA256), 8)
        self.assertEqual(len(p293.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        for digest in list(p293.EXPECTED_COMPACT_DONOR_SHA256.values()) + list(
            p293.EXPECTED_LARGE_HEAD4K_SHA256.values()
        ):
            self.assertEqual(len(digest), 64)

    def test_12_local_donor_tokens_and_sha_verified_when_present(self) -> None:
        if self.default_audit["source_mode"] == p293.SOURCE_MODE_LOCAL_DONOR:
            da = self.default_audit["donor_audit"]
            for key in p293.EXPECTED_COMPACT_DONOR_SHA256:
                self.assertTrue(da[key]["sha256_verified"], msg=key)
            for key in p293.EXPECTED_LARGE_HEAD4K_SHA256:
                self.assertTrue(da[key]["head_sha256_verified"], msg=key)
                self.assertTrue(da[key]["bounded_windows_only"], msg=key)
        else:
            self.assertEqual(self.default_audit["source_mode"], p293.SOURCE_MODE_CLEAN_ROOM)

    def test_13_no_hardcoded_usr_bin_python3_in_stage59_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py"
        ).read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, test_src)

    def test_14_redlines_dict_locks_all_hardware_safety_fields(self) -> None:
        red = self.clean_audit["redlines"]
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertFalse(red["hardware_live_attachment_authorized"])
        self.assertFalse(red["overall_ready_for_hardware_attach"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        self.assertEqual(red["emmc_nflasha_write_count"], 0)
        self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(red["dormant_lossless_raw_exposed_events"], 0)
        self.assertEqual(red["slot1_vault_still_or_burst_write_events"], 0)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 59A — Still [Image Quality Settings], Dormant
    #          Lossless Raw Gate, HEIF 10-bit & HLG Still Image (16 tests)
    # ------------------------------------------------------------------
    def test_15_fx3_exposed_raw_types_compressed_and_uncompressed_only_14bit(self) -> None:
        self.assertEqual(len(p293.EXPOSED_FX3_RAW_FILE_TYPES), 2)
        for raw_t in p293.EXPOSED_FX3_RAW_FILE_TYPES:
            r = p293.simulate_still_raw_heif_hlg_hil(
                configured_file_format=p293.STILL_FMT_RAW,
                configured_raw_file_type=raw_t,
            )
            self.assertTrue(r.admitted, msg=raw_t)
            self.assertEqual(r.effective_raw_file_type, raw_t)
            self.assertEqual(r.raw_bit_depth, 14)
            self.assertEqual(r.output_extensions, (".ARW",))
            self.assertTrue(r.dormant_lossless_gated_out)

    def test_16_all_4_dormant_lossless_raw_variants_rejected_eopnotsupp(self) -> None:
        self.assertEqual(len(p293.DORMANT_LOSSLESS_RAW_TYPES), 4)
        for dormant in p293.DORMANT_LOSSLESS_RAW_TYPES:
            r = p293.simulate_still_raw_heif_hlg_hil(
                configured_file_format=p293.STILL_FMT_RAW,
                configured_raw_file_type=dormant,
            )
            self.assertFalse(r.admitted, msg=dormant)
            self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO, msg=dormant)
            self.assertEqual(r.reason_code, "DORMANT_LOSSLESS_RAW_GATED_OUT_ON_FX3_702")
            self.assertTrue(r.dormant_lossless_gated_out)
            self.assertEqual(r.dormant_lossless_raw_exposed_events, 0)

    def test_17_jpeg_vs_heif_420_and_422_10bit_extensions_and_bitdepth(self) -> None:
        j = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_JPEG,
            configured_file_format=p293.STILL_FMT_JPEG,
        )
        self.assertTrue(j.admitted)
        self.assertEqual(j.non_raw_bit_depth, 8)
        self.assertEqual(j.output_extensions, (".JPG",))

        for hsw in (p293.JH_SWITCH_HEIF_420, p293.JH_SWITCH_HEIF_422):
            h = p293.simulate_still_raw_heif_hlg_hil(
                configured_jpeg_heif_switch=hsw,
                configured_file_format=p293.STILL_FMT_HEIF,
            )
            self.assertTrue(h.admitted, msg=hsw)
            self.assertEqual(h.non_raw_bit_depth, 10)
            self.assertEqual(h.output_extensions, (".HIF",))

    def test_18_raw_plus_jpeg_and_raw_plus_heif_dual_extensions_and_switch_match(self) -> None:
        rj = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_JPEG,
            configured_file_format=p293.STILL_FMT_RAW_JPEG,
        )
        self.assertTrue(rj.admitted)
        self.assertEqual(rj.output_extensions, (".ARW", ".JPG"))

        rh = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_422,
            configured_file_format=p293.STILL_FMT_RAW_HEIF,
        )
        self.assertTrue(rh.admitted)
        self.assertEqual(rh.output_extensions, (".ARW", ".HIF"))

        mismatch_heif_with_jpg_sw = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_JPEG,
            configured_file_format=p293.STILL_FMT_HEIF,
        )
        self.assertFalse(mismatch_heif_with_jpg_sw.admitted)
        self.assertEqual(mismatch_heif_with_jpg_sw.errno_code, p293.EOPNOTSUPP_ERRNO)

        mismatch_jpg_with_heif_sw = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_420,
            configured_file_format=p293.STILL_FMT_JPEG,
        )
        self.assertFalse(mismatch_jpg_with_heif_sw.admitted)
        self.assertEqual(mismatch_jpg_with_heif_sw.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_19_hlg_still_image_on_requires_heif_switch_and_heif_only_and_pasm(self) -> None:
        for hsw in (p293.JH_SWITCH_HEIF_420, p293.JH_SWITCH_HEIF_422):
            for mode in p293.PASM_EXPOSURE_MODES:
                r = p293.simulate_still_raw_heif_hlg_hil(
                    exposure_mode=mode,
                    configured_jpeg_heif_switch=hsw,
                    configured_file_format=p293.STILL_FMT_HEIF,
                    configured_hlg_still_image=p293.TOGGLE_ON,
                )
                self.assertTrue(r.admitted, msg=f"{hsw}/{mode}")
                self.assertEqual(r.effective_hlg_still_image, p293.TOGGLE_ON)
                self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_BT2100)
                self.assertTrue(r.pp_creativelook_dro_locked_by_hlg)
                self.assertTrue(r.dro_bracket_locked_by_hlg)

    def test_20_hlg_still_image_blocked_under_jpeg_raw_raw_heif_and_iauto(self) -> None:
        for sw, fmt in (
            (p293.JH_SWITCH_JPEG, p293.STILL_FMT_JPEG),
            (p293.JH_SWITCH_JPEG, p293.STILL_FMT_RAW),
            (p293.JH_SWITCH_JPEG, p293.STILL_FMT_RAW_JPEG),
            (p293.JH_SWITCH_HEIF_420, p293.STILL_FMT_RAW),
            (p293.JH_SWITCH_HEIF_422, p293.STILL_FMT_RAW_HEIF),
        ):
            r = p293.simulate_still_raw_heif_hlg_hil(
                exposure_mode=p293.EXPOSURE_MODE_M,
                configured_jpeg_heif_switch=sw,
                configured_file_format=fmt,
                configured_hlg_still_image=p293.TOGGLE_ON,
            )
            self.assertFalse(r.admitted, msg=f"{sw}/{fmt}")
            self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

        iauto = p293.simulate_still_raw_heif_hlg_hil(
            exposure_mode=p293.EXPOSURE_MODE_IAUTO,
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_420,
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_hlg_still_image=p293.TOGGLE_ON,
        )
        self.assertFalse(iauto.admitted)
        self.assertEqual(iauto.errno_code, p293.EOPNOTSUPP_ERRNO)
        self.assertEqual(iauto.reason_code, "HLG_STILL_BLOCKED_IN_IAUTO_REQUIRES_PASM")

    def test_21_hlg_still_image_locks_pp_creativelook_dro_and_dro_bracket(self) -> None:
        for flag in (
            {"requested_pp_or_creativelook_override": True},
            {"requested_dro_override": True},
            {"requested_dro_bracket_override": True},
        ):
            r = p293.simulate_still_raw_heif_hlg_hil(
                configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_422,
                configured_file_format=p293.STILL_FMT_HEIF,
                configured_hlg_still_image=p293.TOGGLE_ON,
                **flag,
            )
            self.assertFalse(r.admitted, msg=str(flag))
            self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO, msg=str(flag))

    def test_22_hlg_still_gamma_display_assist_auto_and_hlg_bt2020(self) -> None:
        for assist in p293.VALID_HLG_GAMMA_ASSIST_TYPES:
            r = p293.simulate_still_raw_heif_hlg_hil(
                configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_420,
                configured_file_format=p293.STILL_FMT_HEIF,
                configured_hlg_still_image=p293.TOGGLE_ON,
                configured_gamma_assist_type=assist,
            )
            self.assertTrue(r.admitted, msg=assist)
            self.assertEqual(r.effective_gamma_display_assist, assist)

        off_assist = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_420,
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_hlg_still_image=p293.TOGGLE_OFF,
        )
        self.assertTrue(off_assist.admitted)
        self.assertEqual(off_assist.effective_gamma_display_assist, p293.TOGGLE_OFF)

    def test_23_hlg_still_and_quality_settings_reset_restore_defaults(self) -> None:
        for ra in (p293.RESET_ACTION_CAMERA_SETTINGS_RESET, p293.RESET_ACTION_INITIALIZE):
            r = p293.simulate_still_raw_heif_hlg_hil(
                configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_422,
                configured_file_format=p293.STILL_FMT_HEIF,
                configured_raw_file_type=p293.RAW_TYPE_UNCOMPRESSED,
                configured_hlg_still_image=p293.TOGGLE_ON,
                reset_action=ra,
            )
            self.assertTrue(r.admitted, msg=ra)
            self.assertTrue(r.restored_to_factory_defaults)
            self.assertEqual(r.effective_raw_file_type, p293.RAW_TYPE_COMPRESSED)
            self.assertEqual(r.effective_hlg_still_image, p293.TOGGLE_OFF)
            self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_SRGB)

    def test_24_fx6_has_zero_still_dcim_pipeline_and_movie_16bit_raw_contrast(self) -> None:
        fx6_still = p293.simulate_still_raw_heif_hlg_hil(
            body_profile=p293.BODY_MODEL_FX6,
            still_capture_requested=True,
        )
        self.assertFalse(fx6_still.admitted)
        self.assertFalse(fx6_still.still_pipeline_present)
        self.assertEqual(fx6_still.errno_code, p293.EOPNOTSUPP_ERRNO)

        fx6_movie = p293.simulate_still_raw_heif_hlg_hil(
            body_profile=p293.BODY_MODEL_FX6,
            still_capture_requested=False,
        )
        self.assertTrue(fx6_movie.admitted)
        self.assertFalse(fx6_movie.still_pipeline_present)
        self.assertEqual(fx6_movie.raw_bit_depth, 16)
        self.assertEqual(fx6_movie.output_extensions, (".MXF", ".MP4"))

    def test_25_fx3a_body_shares_exact_fx3_still_pipeline(self) -> None:
        fx3a = p293.simulate_still_raw_heif_hlg_hil(
            body_profile=p293.BODY_MODEL_FX3A,
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_422,
            configured_file_format=p293.STILL_FMT_RAW_HEIF,
            configured_raw_file_type=p293.RAW_TYPE_UNCOMPRESSED,
        )
        self.assertTrue(fx3a.admitted)
        self.assertTrue(fx3a.still_pipeline_present)
        self.assertEqual(fx3a.output_extensions, (".ARW", ".HIF"))

    def test_26_all_still_quality_and_image_size_combos_admitted(self) -> None:
        for q in p293.VALID_STILL_QUALITIES:
            for sz in p293.VALID_STILL_IMAGE_SIZES:
                r = p293.simulate_still_raw_heif_hlg_hil(
                    configured_quality=q,
                    configured_image_size=sz,
                )
                self.assertTrue(r.admitted, msg=f"{q}/{sz}")
                self.assertEqual(r.configured_quality, q)
                self.assertEqual(r.configured_image_size, sz)

    def test_27_invalid_pillar_a_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "ILME-FX9"},
            {"exposure_mode": "BulbOnly"},
            {"configured_jpeg_heif_switch": "AVIF"},
            {"configured_file_format": "TIFF"},
            {"configured_raw_file_type": "16-bit"},
            {"configured_quality": "UltraRaw"},
            {"configured_image_size": "24M"},
            {"configured_hlg_still_image": "Auto"},
            {"configured_gamma_assist_type": "S-Log3"},
            {"reset_action": "FactoryFlash"},
        ):
            r = p293.simulate_still_raw_heif_hlg_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p293.EINVAL_ERRNO, msg=str(kwargs))

    def test_28_pillar_a_dict_passed_and_zero_physical_writes(self) -> None:
        pa = self.clean_audit["pillar_a_raw_heif_hlg_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["raw_compressed_ok"]["physical_device_writes"], 0)
        self.assertEqual(pa["hlg_still_on_bt2100_ok"]["hlg_still_prerequisite_bypass_events"], 0)
        self.assertEqual(len(pa["dormant_lossless_rejected_matrix"]), 4)

    def test_29_raw_only_ignores_non_raw_bit_depth(self) -> None:
        r = p293.simulate_still_raw_heif_hlg_hil(
            configured_file_format=p293.STILL_FMT_RAW,
            configured_raw_file_type=p293.RAW_TYPE_COMPRESSED,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.non_raw_bit_depth, 0)
        self.assertEqual(r.raw_bit_depth, 14)

    def test_30_hlg_still_image_off_in_heif_defaults_to_srgb(self) -> None:
        r = p293.simulate_still_raw_heif_hlg_hil(
            configured_jpeg_heif_switch=p293.JH_SWITCH_HEIF_420,
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_hlg_still_image=p293.TOGGLE_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_hlg_still_image, p293.TOGGLE_OFF)
        self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_SRGB)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 59B — [Color Space] (sRGB vs AdobeRGB _DSC) &
    #          [Set File Name] Leading-'_' Ban (15 tests)
    # ------------------------------------------------------------------
    def test_31_srgb_default_dsc_prefix_produces_dsc0001(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_RAW_JPEG,
            configured_color_space=p293.COLOR_SPACE_SRGB,
            configured_file_name_prefix="DSC",
            file_number=1,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_SRGB)
        self.assertEqual(r.effective_file_name_prefix, "DSC")
        self.assertFalse(r.leading_underscore_applied_by_adobergb)
        self.assertEqual(r.dcf_folder_path, "DCIM/100MSDCF")
        self.assertEqual(r.sample_still_filenames, ("DSC0001.JPG", "DSC0001.ARW"))

    def test_32_adobergb_automatically_prepends_leading_underscore_to_dsc_and_custom(self) -> None:
        dsc = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_RAW_JPEG,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="DSC",
            file_number=42,
        )
        self.assertTrue(dsc.admitted)
        self.assertTrue(dsc.leading_underscore_applied_by_adobergb)
        self.assertEqual(dsc.effective_file_name_prefix, "_DSC")
        self.assertEqual(dsc.sample_still_filenames, ("_DSC0042.JPG", "_DSC0042.ARW"))

        fx3 = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_RAW_JPEG,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="FX3",
            file_number=7,
        )
        self.assertTrue(fx3.admitted)
        self.assertEqual(fx3.effective_file_name_prefix, "_FX3")
        self.assertEqual(fx3.sample_still_filenames, ("_FX30007.JPG", "_FX30007.ARW"))

    def test_33_set_file_name_allows_underscore_in_positions_2_and_3(self) -> None:
        for prefix in ("A_1", "FX_", "Z__", "9A_"):
            r = p293.simulate_color_space_and_set_file_name_hil(
                configured_file_format=p293.STILL_FMT_JPEG,
                configured_color_space=p293.COLOR_SPACE_SRGB,
                configured_file_name_prefix=prefix,
            )
            self.assertTrue(r.admitted, msg=prefix)
            self.assertEqual(r.effective_file_name_prefix, prefix)

    def test_34_set_file_name_strictly_bans_leading_underscore_einval(self) -> None:
        for bad in ("_FX", "_12", "___", "_DS"):
            r = p293.simulate_color_space_and_set_file_name_hil(
                configured_file_name_prefix=bad,
            )
            self.assertFalse(r.admitted, msg=bad)
            self.assertEqual(r.errno_code, p293.EINVAL_ERRNO, msg=bad)
            self.assertEqual(r.reason_code, "SET_FILE_NAME_LEADING_UNDERSCORE_FORBIDDEN_DCF20")
            self.assertTrue(r.leading_underscore_manual_ban_enforced)
            self.assertEqual(r.color_space_leading_underscore_bypass_events, 0)

    def test_35_set_file_name_rejects_wrong_length_or_non_upper_alnum_einval(self) -> None:
        for bad in ("", "A", "AB", "ABCD", "dsc", "FX!", "FX-", "A B"):
            r = p293.simulate_color_space_and_set_file_name_hil(
                configured_file_name_prefix=bad,
            )
            self.assertFalse(r.admitted, msg=repr(bad))
            self.assertEqual(r.errno_code, p293.EINVAL_ERRNO, msg=repr(bad))

    def test_36_heif_ignores_color_space_setting_and_selects_srgb_or_bt2100(self) -> None:
        heif_off = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_hlg_still_image=p293.TOGGLE_OFF,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="FX3",
        )
        self.assertTrue(heif_off.admitted)
        self.assertTrue(heif_off.color_space_ignored_under_heif)
        self.assertEqual(heif_off.effective_color_space, p293.COLOR_SPACE_SRGB)
        self.assertFalse(heif_off.leading_underscore_applied_by_adobergb)
        self.assertEqual(heif_off.sample_still_filenames, ("FX30001.HIF",))

        heif_on = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_hlg_still_image=p293.TOGGLE_ON,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="FX3",
        )
        self.assertTrue(heif_on.admitted)
        self.assertEqual(heif_on.effective_color_space, p293.COLOR_SPACE_BT2100)
        self.assertEqual(heif_on.sample_still_filenames, ("FX30001.HIF",))

    def test_37_requested_adobergb_under_heif_rejected_eopnotsupp(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_HEIF,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            requested_adobergb_under_heif=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "COLOR_SPACE_ADOBERGB_IGNORED_UNDER_HEIF")

    def test_38_raw_plus_heif_keeps_adobergb_for_raw_companion(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_format=p293.STILL_FMT_RAW_HEIF,
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="DSC",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.color_space_ignored_under_heif)
        self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_ADOBE_RGB)
        self.assertEqual(r.sample_still_filenames, ("_DSC0001.HIF", "_DSC0001.ARW"))

    def test_39_camera_settings_reset_resets_color_space_but_preserves_set_file_name(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="FX3",
            reset_action=p293.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_SRGB)
        self.assertTrue(r.color_space_reset_to_srgb)
        self.assertEqual(r.effective_file_name_prefix, "FX3")
        self.assertTrue(r.set_file_name_survived_camera_reset)
        self.assertFalse(r.set_file_name_wiped_by_initialize)

    def test_40_wipe_set_file_name_on_camera_reset_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_file_name_prefix="FX3",
            reset_action=p293.RESET_ACTION_CAMERA_SETTINGS_RESET,
            wipe_set_file_name_on_camera_reset=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_41_initialize_wipes_both_color_space_and_set_file_name(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            configured_color_space=p293.COLOR_SPACE_ADOBE_RGB,
            configured_file_name_prefix="FX3",
            reset_action=p293.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_color_space, p293.COLOR_SPACE_SRGB)
        self.assertEqual(r.effective_file_name_prefix, "DSC")
        self.assertTrue(r.set_file_name_wiped_by_initialize)
        self.assertFalse(r.set_file_name_survived_camera_reset)

    def test_42_slot1_vault_blocked_erofs_and_slot2_scratch_allowed(self) -> None:
        s1 = p293.simulate_color_space_and_set_file_name_hil(
            storage_target=p293.STORAGE_TARGET_SLOT1_VAULT,
        )
        self.assertFalse(s1.admitted)
        self.assertEqual(s1.errno_code, p293.EROFS_ERRNO)
        self.assertEqual(s1.physical_device_writes, 0)

        s2 = p293.simulate_color_space_and_set_file_name_hil(
            storage_target=p293.STORAGE_TARGET_SLOT2_SCRATCH,
        )
        self.assertTrue(s2.admitted)
        self.assertEqual(s2.physical_device_writes, 0)

    def test_43_fx6_rejected_for_still_color_space_and_set_file_name(self) -> None:
        r = p293.simulate_color_space_and_set_file_name_hil(
            body_profile=p293.BODY_MODEL_FX6,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_44_invalid_pillar_b_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"configured_file_format": "DNG"},
            {"configured_hlg_still_image": "Yes"},
            {"configured_color_space": "ProPhotoRGB"},
            {"file_number": 0},
            {"file_number": 10000},
            {"file_number": True},
            {"storage_target": "SD_ROOT"},
            {"reset_action": "Reboot"},
        ):
            r = p293.simulate_color_space_and_set_file_name_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p293.EINVAL_ERRNO, msg=str(kwargs))

    def test_45_pillar_b_dict_passed_and_zero_physical_writes(self) -> None:
        pb = self.clean_audit["pillar_b_colorspace_setfilename_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["default_set_file_name_prefix"], "DSC")
        self.assertEqual(pb["adobergb_prepend_dsc_ok"]["physical_device_writes"], 0)
        self.assertEqual(
            pb["leading_underscore_ban_einval"]["color_space_leading_underscore_bypass_events"], 0
        )

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 59C — [Shutter Type] Exact 2-Option Split,
    #          Electronic/Silent 5-Lock Matrix, NR, 10fps Drive Mode &
    #          Slot-1 Tier-0 Vault Firewall (23 tests)
    # ------------------------------------------------------------------
    def test_46_shutter_type_exact_2_options_mechanical_and_electronic_only(self) -> None:
        self.assertEqual(
            p293.EXPOSED_FX3_2_SHUTTER_TYPES,
            (p293.SHUTTER_TYPE_MECHANICAL, p293.SHUTTER_TYPE_ELECTRONIC),
        )
        for st in p293.EXPOSED_FX3_2_SHUTTER_TYPES:
            r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                requested_shutter_type=st,
            )
            self.assertTrue(r.admitted, msg=st)
            self.assertEqual(r.effective_shutter_type, st)
            self.assertTrue(r.shutter_type_auto_absent_enforced)

    def test_47_shutter_type_auto_does_not_exist_rejected_einval(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_AUTO_UNSUPPORTED,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EINVAL_ERRNO)
        self.assertEqual(r.reason_code, "FX3_SHUTTER_TYPE_EXACTLY_2_OPTIONS_NO_AUTO")

    def test_48_fx6_has_no_mechanical_shutter_contrast(self) -> None:
        mech = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            body_profile=p293.BODY_MODEL_FX6,
            requested_shutter_type=p293.SHUTTER_TYPE_MECHANICAL,
        )
        self.assertFalse(mech.admitted)
        self.assertFalse(mech.mechanical_shutter_present)
        self.assertEqual(mech.errno_code, p293.EOPNOTSUPP_ERRNO)

        elec = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            body_profile=p293.BODY_MODEL_FX6,
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
        )
        self.assertTrue(elec.admitted)
        self.assertFalse(elec.mechanical_shutter_present)
        self.assertEqual(elec.effective_shutter_type, p293.SHUTTER_TYPE_ELECTRONIC)

    def test_49_electronic_shutter_lock1_flash_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
            flash_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.electronic_5locks_engaged)
        self.assertEqual(len(r.locked_functions), 5)

    def test_50_electronic_shutter_lock2_long_exposure_nr_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
            long_exposure_nr=p293.TOGGLE_ON,
            long_exposure_nr_explicit_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_51_electronic_shutter_lock3_e_front_curtain_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
            e_front_curtain_edit_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_52_electronic_shutter_lock4_bulb_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
            bulb_exposure_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_53_electronic_shutter_lock5_anti_flicker_blocked_eopnotsupp(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_ELECTRONIC,
            anti_flicker_shoot_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_54_silent_mode_engages_5_locks_unless_target_function_override(self) -> None:
        locked = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_MECHANICAL,
            silent_mode=p293.TOGGLE_ON,
            flash_requested=True,
        )
        self.assertFalse(locked.admitted)
        self.assertEqual(locked.errno_code, p293.EOPNOTSUPP_ERRNO)

        overridden = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_MECHANICAL,
            silent_mode=p293.TOGGLE_ON,
            silent_target_override=True,
            flash_requested=True,
        )
        self.assertTrue(overridden.admitted)
        self.assertFalse(overridden.electronic_5locks_engaged)

    def test_55_mechanical_shutter_permits_flash_bulb_and_antiflicker(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_MECHANICAL,
            flash_requested=True,
            anti_flicker_shoot_requested=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.flash_sync_max_fraction, "1/250 s")

        bulb = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            requested_shutter_type=p293.SHUTTER_TYPE_MECHANICAL,
            bulb_exposure_requested=True,
            long_exposure_nr=p293.TOGGLE_ON,
        )
        self.assertTrue(bulb.admitted)
        self.assertTrue(bulb.dark_frame_subtraction_active)

    def test_56_e_front_curtain_survives_camera_reset_and_wiped_by_initialize(self) -> None:
        csr = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_e_front_curtain=p293.TOGGLE_OFF,
            reset_action=p293.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(csr.admitted)
        self.assertEqual(csr.effective_e_front_curtain, p293.TOGGLE_OFF)
        self.assertTrue(csr.efront_curtain_survived_camera_reset)
        self.assertFalse(csr.efront_curtain_wiped_by_initialize)

        wipe_blocked = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_e_front_curtain=p293.TOGGLE_OFF,
            reset_action=p293.RESET_ACTION_CAMERA_SETTINGS_RESET,
            wipe_efront_on_camera_reset=True,
        )
        self.assertFalse(wipe_blocked.admitted)
        self.assertEqual(wipe_blocked.errno_code, p293.EOPNOTSUPP_ERRNO)

        ini = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_e_front_curtain=p293.TOGGLE_OFF,
            reset_action=p293.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(ini.admitted)
        self.assertEqual(ini.effective_e_front_curtain, p293.TOGGLE_ON)
        self.assertTrue(ini.efront_curtain_wiped_by_initialize)

    def test_57_long_exposure_nr_dark_frame_only_at_or_above_1s(self) -> None:
        fast = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            shutter_speed_sec=0.5,
            long_exposure_nr=p293.TOGGLE_ON,
        )
        self.assertTrue(fast.admitted)
        self.assertFalse(fast.dark_frame_subtraction_active)

        slow = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            shutter_speed_sec=1.0,
            long_exposure_nr=p293.TOGGLE_ON,
        )
        self.assertTrue(slow.admitted)
        self.assertTrue(slow.dark_frame_subtraction_active)

    def test_58_long_exposure_nr_blocked_during_continuous_drive(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            long_exposure_nr=p293.TOGGLE_ON,
            long_exposure_nr_explicit_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_59_high_iso_nr_ignored_for_raw_arw_and_locked_in_raw_only(self) -> None:
        for mode in p293.VALID_HIGH_ISO_NR_MODES:
            rj = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                configured_file_format=p293.STILL_FMT_RAW_JPEG,
                high_iso_nr=mode,
            )
            self.assertTrue(rj.admitted, msg=mode)
            self.assertTrue(rj.high_iso_nr_ignored_for_raw_arw)
            self.assertEqual(rj.effective_high_iso_nr_for_jpeg_heif, mode)

        raw_only_locked = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_file_format=p293.STILL_FMT_RAW,
            high_iso_nr_explicit_requested=True,
        )
        self.assertFalse(raw_only_locked.admitted)
        self.assertEqual(raw_only_locked.errno_code, p293.EOPNOTSUPP_ERRNO)

    def test_60_all_8_base_and_11_discrete_drive_modes_supported(self) -> None:
        self.assertEqual(len(p293.FX3_8_DRIVE_BASE_MODES), 8)
        self.assertEqual(len(p293.VALID_DRIVE_MODES), 11)
        for dm in p293.VALID_DRIVE_MODES:
            r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                configured_drive_mode=dm,
            )
            self.assertTrue(r.admitted, msg=dm)
            self.assertEqual(r.configured_drive_mode, dm)

    def test_61_cont_shooting_hi_plus_10fps_with_compressed_raw_or_jpeg(self) -> None:
        for fmt in (p293.STILL_FMT_JPEG, p293.STILL_FMT_RAW_JPEG, p293.STILL_FMT_RAW):
            r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
                configured_file_format=fmt,
                configured_raw_file_type=p293.RAW_TYPE_COMPRESSED,
                burst_frames_captured=200,
            )
            self.assertTrue(r.admitted, msg=fmt)
            self.assertEqual(r.effective_burst_fps, 10.0)
            self.assertFalse(r.uncompressed_raw_speed_drop_active)

    def test_62_uncompressed_raw_and_flash_drop_hi_plus_from_10fps_to_8fps(self) -> None:
        uncomp = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            configured_file_format=p293.STILL_FMT_RAW,
            configured_raw_file_type=p293.RAW_TYPE_UNCOMPRESSED,
        )
        self.assertTrue(uncomp.admitted)
        self.assertTrue(uncomp.uncompressed_raw_speed_drop_active)
        self.assertEqual(uncomp.effective_burst_fps, 8.0)

        flash_drop = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            configured_file_format=p293.STILL_FMT_JPEG,
            flash_requested=True,
        )
        self.assertTrue(flash_drop.admitted)
        self.assertEqual(flash_drop.effective_burst_fps, 8.0)

    def test_63_burst_ge_1000_triggers_slow_throttle_and_gt_f11_locks_af(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            aperture_f_number=16.0,
            burst_frames_captured=1000,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.buffer_slow_throttled)
        self.assertLessEqual(r.effective_burst_fps, 4.0)
        self.assertTrue(r.af_locked_past_f11)

        f11 = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            aperture_f_number=11.0,
            burst_frames_captured=999,
        )
        self.assertTrue(f11.admitted)
        self.assertFalse(f11.buffer_slow_throttled)
        self.assertFalse(f11.af_locked_past_f11)

    def test_64_hlg_still_image_on_blocks_dro_bracket_in_drive_mode(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_DRO_BRACKET,
            configured_hlg_still_image=p293.TOGGLE_ON,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p293.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.reason_code, "HLG_STILL_LOCKS_OUT_DRO_BRACKET")

    def test_65_slot1_vault_blocks_still_burst_and_bracket_writes_erofs_and_ebusy(self) -> None:
        for dm in (p293.DRIVE_SINGLE, p293.DRIVE_CONT_HI_PLUS, p293.DRIVE_CONT_BRACKET):
            erofs = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                configured_drive_mode=dm,
                storage_target=p293.STORAGE_TARGET_SLOT1_VAULT,
            )
            self.assertFalse(erofs.admitted, msg=dm)
            self.assertEqual(erofs.errno_code, p293.EROFS_ERRNO, msg=dm)
            self.assertTrue(erofs.slot1_vault_blocked)
            self.assertEqual(erofs.slot1_vault_still_or_burst_write_events, 0)
            self.assertEqual(erofs.physical_device_writes, 0)

            ebusy = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
                configured_drive_mode=dm,
                storage_target=p293.STORAGE_TARGET_SLOT1_VAULT,
                slot1_busy_locked=True,
            )
            self.assertFalse(ebusy.admitted, msg=dm)
            self.assertEqual(ebusy.errno_code, p293.EBUSY_ERRNO, msg=dm)
            self.assertTrue(ebusy.slot1_vault_blocked)

    def test_66_slot2_scratch_permits_10fps_burst_with_zero_physical_writes(self) -> None:
        r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(
            configured_drive_mode=p293.DRIVE_CONT_HI_PLUS,
            storage_target=p293.STORAGE_TARGET_SLOT2_SCRATCH,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.slot1_vault_blocked)
        self.assertEqual(r.effective_burst_fps, 10.0)
        self.assertEqual(r.physical_device_writes, 0)

    def test_67_invalid_pillar_c_params_rejected_einval(self) -> None:
        for kwargs in (
            {"body_profile": "UNKNOWN"},
            {"exposure_mode": "MovieOnly"},
            {"requested_shutter_type": "LeafShutter"},
            {"configured_e_front_curtain": "Auto"},
            {"silent_mode": "Half"},
            {"long_exposure_nr": "Auto"},
            {"high_iso_nr": "Extreme"},
            {"configured_drive_mode": "Cont. Ultra"},
            {"shutter_speed_sec": 0.0},
            {"shutter_speed_sec": True},
            {"aperture_f_number": -1.4},
            {"aperture_f_number": True},
            {"burst_frames_captured": -1},
            {"burst_frames_captured": True},
        ):
            r = p293.simulate_shutter_type_nr_drive_and_slot1_vault_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p293.EINVAL_ERRNO, msg=str(kwargs))

    def test_68_pillar_cd_dict_passed_and_covers_all_5_locks_and_16_redlines(self) -> None:
        pcd = self.default_audit["pillar_c_d_shutter_nr_drive_vault_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["eshutter_5lock_matrix"]), 5)
        self.assertEqual(len(pcd["all_16_redline_probe_fields"]), 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 16)
        self.assertTrue(pcd["baseline_redline_guard"]["valid"])

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 59 (59/59) Suite & Subprocess
    #          Portability Hygiene (10 tests -> Total 78)
    # ------------------------------------------------------------------
    def test_69_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p293.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p293.probe_phase293_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p293.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p293.probe_phase293_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.dormant_lossless_raw_exposed_events, 0)
            self.assertEqual(blocked.hlg_still_prerequisite_bypass_events, 0)
            self.assertEqual(blocked.color_space_leading_underscore_bypass_events, 0)
            self.assertEqual(blocked.shutter_type_auto_or_5lock_bypass_events, 0)
            self.assertEqual(blocked.slot1_vault_still_or_burst_write_events, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p293.probe_phase293_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p293.EINVAL_ERRNO)

    def test_70_standalone_cli_self_test_summary_json_and_help_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p293.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 293 Stage 59 (59/59)", proc_sum.stdout)
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
        self.assertEqual(data["milestone"], "59/59")
        self.assertEqual(data["phase_number"], 293)

        proc_help = subprocess.run(
            [sys.executable, "-B", script, "--help"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--clean-room", proc_help.stdout)

    def test_71_standalone_cli_in_process_clean_room_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p293.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 293 Stage 59 (59/59)", buf.getvalue())
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf.getvalue())

    def test_72_suite_stage59_59_of_59_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s59 = rep["stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil"]
            self.assertTrue(s59["all_checks_passed"])
            self.assertEqual(s59["phase_number"], 293)
            self.assertEqual(s59["milestone"], "59/59")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 59)

    def test_73_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 15.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_74_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_75_suite_stage59_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil
        )
        self.assertTrue(default_cfg.include_stage59)
        self.assertTrue(
            default_cfg.include_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil
        )

        for override in (
            {"stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil": False},
            {"include_stage59": False},
            {"include_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage59"])
            self.assertFalse(
                rep["config"]["stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil"]
            )

    def test_76_fx3_vm_coemulation_suite_include_stage59_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage59", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_raw_heif_colorspace_shuttertype_nr_drive_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_77_fx3_vm_coemulation_suite_cli_skip_phase293_and_skip_stage59(self) -> None:
        for skip_flag in ("--skip-phase293", "--skip-stage59", "--no-include-stage59"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0, msg=skip_flag)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"], msg=skip_flag)
            self.assertNotIn(
                "stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil", rep
            )

    def test_78_suite_help_works_without_argparse_percent_errors(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                suite.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("--include-stage59", buf.getvalue())
        self.assertIn("--skip-stage59", buf.getvalue())
        self.assertIn("--skip-phase293", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
