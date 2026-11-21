#!/usr/bin/env python3
"""Unit tests for Phase 372 (Stage 85 — 85/85 Full-Board VM Co-Emulation Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-75 Milestone:
- 85A: `[Metering Mode]` 6-Mode Matrix (`Multi`..`Highlight`, CIZ lock),
  `[Face Priority in Multi Metering]` (`BKID_APP_setting_face_detection_in_multi`),
  `[Spot Metering Point]` (`Center`/`Focus Point Link`), Still-only Reset-resistant
  `[AEL w/ Shutter]` vs Movie Custom-Key AEL, and Wave-75 `G96` `[Exposure step]`
  Erratum (`Not available` under `[Camera Settings Reset]`, `Initialize`-only,
  `[Shutter Angle]` immune, `Cine EI` `M.M.` locked to Base ISO) vs `ILME-FX6`
  `Auto Exposure` (`Level -3.0..+3.0` in `0.25` = 25 steps, disproving
  `-2.0..+2.0EV` rumor; `Speed -99..+99`; `Detect Window 1..6/Custom`),
- 85B: `[Picture Profile]` (`Off`, `PP1..11` def `PP11 S-Cinetone`, Movie-only
  `PPLUT1..4` baking `.cube` & 1080p HDMI clamp) Asymmetric Reset/Initialize
  Split (`PP1..11` custom params & `[Different Set for Still/Mv]` PP checkbox
  resist BOTH Reset and Initialize; `PPLUT1..4` reset on both), `User1..16`
  `.cube` (`17`/`33`-pt `<= 63` chars from `/Private/Sony/PRO/LUT` or
  `/Sony/PRO/LUT`), & `[Embed LUT File]` (SD/SDHC lock, **MP4** only, zero MXF,
  zero sidecar) vs FX6 `Base Look` + 16-axis `Multi Matrix` + 4-bus `MLUT` + MXF,
- 85C: 5-Axis IBIS `[SteadyShot]` (`Active` ~`1.1x` forcing `Distortion Comp. =
  Auto`, `Standard` def, `Off`), exact **47-entry** discrete `[SteadyShot
  Focal Len.]` table (`8..1000mm`, def `8mm`, all 4 Resettable; dormant
  `Dynamic active`/`Intelligent Active`/`Super Active` rejected), `Active`
  4 lockouts (`>=100p`, `S&Q >= 100fps`, `HDMI RAW=On`, `De-Squeeze != Off`), &
  Catalyst Gyro (`Off`/`Active` only + E-mount, absent `120p` & all `S&Q`) vs
  FX6 zero physical IBIS (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`, optical
  OSS `On/Off` only, dormant Focal Length rejected),
- 85D: Zero-Sector-Write Playback Viewing (`[Image Index]` `9`/`25` Images,
  dormant `12`/`30` rejected, `[Display Rotation]` `BKID_APP_setting_display_rotatiton`,
  `[Focus Frame Display]`, `[Cont. PB for Interval]`, `[Play Speed for Interval]`
  `1..9` def `5` — all 0 writes & Reset-resistant) vs Still DCF (`4,000`/folder)
  & Movie `[Cam ID + Reel#]` 17-char stem (`A001C001_230101AB`, `C999->D001`,
  SDHC lock) separated from **`37`-char `[Title Name Settings]`** (def `"C"`) vs
  FX6 `Clip Name Format` (`Title Prefix` `4..46` def `nnn_` -> `/XDROOT/Clip/*.MXF`),
  plus Tier-0 `Slot 1 EROFS=30` Firewall (`[Create New Folder]`, `[Forced File No.
  Reset]`, `[Select REC Folder]`, `[Series Counter Reset]`)
HIL (104 four-mode tests).
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
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_metering_pplut_ibis47_camid_pbfile_coemulator as p372  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..84 for Stage 85 isolation."""
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
        include_stage69=False,
        include_stage70=False,
        include_stage71=False,
        include_stage72=False,
        include_stage73=False,
        include_stage74=False,
        include_stage75=False,
        include_stage76=False,
        include_stage77=False,
        include_stage78=False,
        include_stage79=False,
        include_stage80=False,
        include_stage81=False,
        include_stage82=False,
        include_stage83=False,
        include_stage84=False,
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
    "--skip-stage69",
    "--skip-stage70",
    "--skip-stage71",
    "--skip-stage72",
    "--skip-stage73",
    "--skip-stage74",
    "--skip-stage75",
    "--skip-stage76",
    "--skip-stage77",
    "--skip-stage78",
    "--skip-stage79",
    "--skip-stage80",
    "--skip-stage81",
    "--skip-stage82",
    "--skip-stage83",
    "--skip-stage84",
]


class TestPhase372Stage85MeteringPPLUTIBIS47CamIDPBFile(unittest.TestCase):
    # =========================================================================
    # Tests 01..15: Schema, 85/85 Milestone, Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_phase_and_85_of_85_milestone_constants(self) -> None:
        self.assertEqual(
            p372.SCHEMA_ID,
            "phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation_v1",
        )
        self.assertEqual(p372.PHASE_NUMBER, 372)
        self.assertEqual(p372.STAGE_INDEX, 85)
        self.assertEqual(p372.STAGE_TOTAL, 85)
        self.assertEqual(p372.MILESTONE_LABEL, "85/85")
        self.assertTrue(p372.IS_85TH_STAGE_MILESTONE)
        self.assertFalse(p372.READY_FOR_LIVE_CAMERA_ATTACH)

    def test_02_orchestrator_returns_stage85_milestone_and_zero_redlines(self) -> None:
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["phase_number"], 372)
        self.assertEqual(rep["stage_index"], 85)
        self.assertEqual(rep["stage_total"], 85)
        self.assertEqual(rep["milestone"], "85/85")
        self.assertTrue(rep["is_85th_stage_milestone"])
        self.assertEqual(rep["nop_count"], 0)
        self.assertEqual(rep["guest_code_modification_bytes"], 0)
        self.assertEqual(rep["cp_mutation_bytes"], 0)
        self.assertEqual(rep["wbi_mutation_bytes"], 0)
        self.assertEqual(rep["calibration_mutation_bytes"], 0)
        self.assertEqual(rep["cnflasha_mutation_bytes"], 0)
        self.assertTrue(rep["cnflasha_userspace_write_blocked"])
        self.assertEqual(rep["nvram_persistent_writes"], 0)
        self.assertEqual(rep["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(rep["physical_device_writes"], 0)
        self.assertFalse(rep["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["emmc_writes_authorized"])
        self.assertFalse(rep["cross_model_flash_authorized"])
        self.assertFalse(rep["hardware_live_attachment_authorized"])
        self.assertFalse(rep["overall_ready_for_hardware_attach"])
        self.assertFalse(rep["isp_write_authorized"])
        self.assertEqual(rep["emmc_nflasha_write_count"], 0)
        self.assertEqual(rep["emmc_mutation_bytes"], 0)
        self.assertEqual(rep["emmc_corruptions"], 0)
        self.assertFalse(rep["spi_nor_write_authorized"])
        self.assertEqual(rep["spi_nor_mutation_bytes"], 0)
        self.assertFalse(rep["el3_payload_transmit_authorized"])
        self.assertEqual(rep["otp_fuse_touches"], 0)
        self.assertEqual(rep["rpmb_counter_increments"], 0)
        self.assertEqual(rep["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["passive_tx_bytes_emitted"], 0)
        self.assertEqual(rep["slot1_sector_writes"], 0)
        self.assertEqual(rep["slot1_data_sector_writes"], 0)
        self.assertFalse(rep["slot1_avf_info_mutated"])
        self.assertEqual(rep["rf_tx_packets"], 0)
        self.assertEqual(rep["rf_packets_transmitted"], 0)
        self.assertEqual(rep["rf_nvs_mutation_bytes"], 0)
        self.assertEqual(rep["rsv_orphan_count"], 0)
        self.assertEqual(rep["null_gpio_derefs"], 0)
        self.assertEqual(rep["mailbox_stalls"], 0)
        self.assertEqual(rep["stock_cp_fault_count"], 0)
        self.assertEqual(rep["wf12_00342260_hits"], 0)
        self.assertEqual(rep["appfw_crashes"], 0)
        self.assertEqual(rep["raw_firmware_bytes_leaked"], 0)

    def test_03_donor_spec_counts_15_compact_plus_4_window_equals_19(self) -> None:
        self.assertEqual(len(p372.PHASE372_COMPACT_DONORS), 15)
        self.assertEqual(len(p372.PHASE372_WINDOW_DONORS), 4)
        names = [d.name for d in p372.PHASE372_COMPACT_DONORS] + [
            d.name for d in p372.PHASE372_WINDOW_DONORS
        ]
        self.assertEqual(len(names), 19)
        self.assertEqual(len(set(names)), 19)

    def test_04_donor_inspection_force_clean_room_env(self) -> None:
        info = p372.inspect_phase372_wave75_donors(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(info["total_donors_count"], 19)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_05_donor_inspection_clean_room_test_env(self) -> None:
        info = p372.inspect_phase372_wave75_donors(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["total_donors_count"], 19)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(info["all_donors_verified"])

    def test_06_donor_inspection_donorless_work_root_none_and_sentinel(self) -> None:
        d1 = p372.inspect_phase372_wave75_donors(work_root=None)
        d2 = p372.inspect_phase372_wave75_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p372._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(d1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d2["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d1["total_donors_count"], 19)
        self.assertEqual(d2["total_donors_count"], 19)
        self.assertEqual(d1["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(d2["raw_firmware_bytes_leaked"], 0)

    def test_07_window_donors_bounded_pread_4096_cap_and_o_rdonly(self) -> None:
        info = p372.inspect_phase372_wave75_donors(work_root=None)
        for entry in info["window_donors"]:
            self.assertGreater(entry["windows_verified"], 0)
            self.assertLessEqual(entry["max_pread_bytes"], 4096)

    def test_08_real_local_donors_if_present_verify_strictly_readonly_zero_leak(self) -> None:
        info = p372.inspect_phase372_wave75_donors()
        self.assertIn(
            info["source_mode"],
            ("LOCAL_O_RDONLY_REAL_DONORS", "CLEAN_ROOM_SYNTHETIC"),
        )
        if info["source_mode"] == "LOCAL_O_RDONLY_REAL_DONORS":
            self.assertEqual(info["donor_access_mode"], "O_RDONLY_BOUNDED_4K_AND_COMPACT")
        self.assertEqual(info["total_donors_count"], 19)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(info["all_donors_verified"])

    def test_09_compact_donor_tokens_cover_all_4_submodels_and_disproofs(self) -> None:
        en = next(
            d for d in p372.PHASE372_COMPACT_DONORS if d.name == "fx3_string_en_f"
        )
        for tok in (
            b"Metering Mode",
            b"AEL w/ Shutter",
            b"Exposure step",
            b"Picture Profile",
            b"Manage User LUTs",
            b"Embed LUT File",
            b"SteadyS. Focal Len.",
            b"25 Images",
            b"Display Rotation",
            b"Cam ID + Reel#",
            b"Title Name Settings",
        ):
            self.assertIn(tok, en.required_tokens)
        for abs_tok in (b"Multi Matrix", b"Detect Window", b"All File"):
            self.assertIn(abs_tok, en.absent_tokens)

    def test_10_window_donor_absent_tokens_disprove_dormant_steadyshot_and_bk4_typos(self) -> None:
        fx3_appfw = next(
            d for d in p372.PHASE372_WINDOW_DONORS if d.name == "fx3_appfw"
        )
        abs_bytes = [b for _, _, b in fx3_appfw.absent_windows]
        self.assertIn(b"STEADYSHOT_DYNAMIC_ACTIVE", abs_bytes)
        self.assertIn(b"INTELLIGENT_ACTIVE", abs_bytes)
        self.assertIn(b"SUPER_ACTIVE", abs_bytes)

        appfw_win_bytes = [b for _, _, b in fx3_appfw.windows]
        self.assertIn(b"BKID_APP_setting_face_detection_in_multi", appfw_win_bytes)
        self.assertIn(b"BKID_APP_setting_display_rotatiton", appfw_win_bytes)
        self.assertIn(b"BKID_APP_MR_setting_pplut1_link_uset_lut", appfw_win_bytes)

        fx3_bk4 = next(d for d in p372.PHASE372_WINDOW_DONORS if d.name == "fx3_bk4")
        self.assertIn(b"BK4\x00", [b for _, _, b in fx3_bk4.windows])
        self.assertIn(b"ILME-FX3", [b for _, _, b in fx3_bk4.windows])

    def test_11_compact_donors_absent_fx6_steadyshot_focal_and_ibis(self) -> None:
        fx6_w = next(d for d in p372.PHASE372_WINDOW_DONORS if d.name == "fx6_appfw")
        self.assertIn(
            b"TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED",
            [b for _, _, b in fx6_w.windows],
        )

    def test_12_stage85_milestone_probe_submodels_all_true(self) -> None:
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        probe = rep["stage85_milestone_probe"]
        self.assertEqual(probe["stage_index"], 85)
        self.assertEqual(probe["stage_total"], 85)
        self.assertEqual(probe["milestone_label"], "85/85")
        self.assertTrue(probe["is_85th_stage_milestone"])
        self.assertTrue(probe["submodel_85a_passed"])
        self.assertTrue(probe["submodel_85b_passed"])
        self.assertTrue(probe["submodel_85c_passed"])
        self.assertTrue(probe["submodel_85d_passed"])
        self.assertFalse(probe["ready_for_live_camera_attach"])

    def test_13_audit_digest_64_hex_chars_and_zero_wall_clock_influence(self) -> None:
        r1 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        r2 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        self.assertRegex(r1["phase372_audit_digest_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            r1["phase372_audit_digest_sha256"],
            r2["phase372_audit_digest_sha256"],
        )

    def test_14_explicit_redline_constants_exact_values(self) -> None:
        self.assertEqual(p372.EROFS_ERRNO, 30)
        self.assertEqual(p372.EINVAL_ERRNO, 22)
        self.assertEqual(p372.EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(p372.EPERM_ERRNO, 1)
        self.assertEqual(p372.NOP_COUNT, 0)
        self.assertEqual(p372.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_15_mocked_work_root_does_not_leak_tokens_in_error(self) -> None:
        info = p372.inspect_phase372_wave75_donors(work_root="/nonexistent_stage85_dir")
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    # =========================================================================
    # Tests 16..38: Sub-Model 85A — Exposure & Metering Matrix, AEL w/ Shutter,
    #               G96 [Exposure step] Erratum & FX6 -3.0..+3.0 AE Level
    # =========================================================================

    def test_16_85a_fx3_all_6_metering_modes_accepted_default_multi(self) -> None:
        self.assertEqual(len(p372.FX3_METERING_MODES), 6)
        self.assertEqual(p372.FX3_METERING_MODE_DEFAULT, "Multi")
        for mode in p372.FX3_METERING_MODES:
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_metering_6mode_and_ciz_lock",
                metering_mode=mode,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.errno, 0)
            self.assertEqual(r.metering_mode, mode)

    def test_17_85a_fx3_invalid_metering_mode_rejected_einval(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_metering_6mode_and_ciz_lock",
            metering_mode="Matrix",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p372.EINVAL_ERRNO)

    def test_18_85a_fx3_ciz_or_digital_zoom_locks_metering_to_multi(self) -> None:
        for mode in ("Center", "Spot: Standard", "Spot: Large", "Entire Screen Avg.", "Highlight"):
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_metering_6mode_and_ciz_lock",
                metering_mode=mode,
                non_optical_zoom_active=True,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.metering_mode, "Multi")

        r_multi = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_metering_6mode_and_ciz_lock",
            metering_mode="Multi",
            non_optical_zoom_active=True,
        )
        self.assertTrue(r_multi.allowed)
        self.assertEqual(r_multi.metering_mode, "Multi")

    def test_19_85a_fx3_face_priority_in_multi_symbol_and_locks(self) -> None:
        self.assertEqual(
            p372.FX3_FACE_PRIORITY_SYMBOL,
            "BKID_APP_setting_face_detection_in_multi",
        )
        r_ok = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_face_priority_multi_locks",
            metering_mode="Multi",
            desqueeze_display="Off",
            non_optical_zoom_active=False,
            face_priority_requested=True,
        )
        self.assertTrue(r_ok.allowed)
        self.assertTrue(r_ok.face_priority_in_multi)

        r_not_multi = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_face_priority_multi_locks",
            metering_mode="Center",
            face_priority_requested=True,
        )
        self.assertFalse(r_not_multi.allowed)
        self.assertFalse(r_not_multi.face_priority_in_multi)

        for desq in ("1.3x", "1.5x", "1.6x", "2.0x"):
            r_desq = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_face_priority_multi_locks",
                metering_mode="Multi",
                desqueeze_display=desq,
                face_priority_requested=True,
            )
            self.assertFalse(r_desq.allowed)
            self.assertEqual(r_desq.errno, p372.EOPNOTSUPP_ERRNO)
            self.assertFalse(r_desq.face_priority_in_multi)

        r_ciz = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_face_priority_multi_locks",
            metering_mode="Multi",
            non_optical_zoom_active=True,
            face_priority_requested=True,
        )
        self.assertFalse(r_ciz.allowed)
        self.assertFalse(r_ciz.face_priority_in_multi)

    def test_20_85a_fx3_spot_metering_point_center_vs_focus_point_link(self) -> None:
        for spot_m in ("Spot: Standard", "Spot: Large"):
            r_link = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_spot_metering_point_coupling",
                metering_mode=spot_m,
                spot_metering_point="Focus Point Link",
                focus_area="Spot: M",
            )
            self.assertTrue(r_link.allowed)
            self.assertEqual(r_link.spot_metering_point, "Focus Point Link")

        for fixed_fa in ("Wide", "Zone", "Center Fix"):
            r_forced = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_spot_metering_point_coupling",
                metering_mode="Spot: Standard",
                spot_metering_point="Focus Point Link",
                focus_area=fixed_fa,
            )
            self.assertTrue(r_forced.allowed)
            self.assertEqual(r_forced.spot_metering_point, "Center")

        r_nonspot = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_spot_metering_point_coupling",
            metering_mode="Multi",
            spot_metering_point="Focus Point Link",
        )
        self.assertFalse(r_nonspot.allowed)
        self.assertEqual(r_nonspot.errno, p372.EOPNOTSUPP_ERRNO)

    def test_21_85a_fx3_ael_w_shutter_still_only_vs_movie_custom_keys(self) -> None:
        for ael in ("Auto", "On", "Off"):
            r_st = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_ael_w_shutter_vs_movie_custom_key",
                shoot_mode="Still",
                ael_w_shutter=ael,
            )
            self.assertTrue(r_st.allowed)
            self.assertEqual(r_st.ael_w_shutter, ael)

        for mv_mode in ("Movie", "S&Q"):
            r_mv_blk = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_ael_w_shutter_vs_movie_custom_key",
                shoot_mode=mv_mode,
                ael_w_shutter="On",
            )
            self.assertFalse(r_mv_blk.allowed)
            self.assertEqual(r_mv_blk.errno, p372.EOPNOTSUPP_ERRNO)

        for ck in p372.FX3_MOVIE_AEL_CUSTOM_KEYS:
            r_ck = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_ael_w_shutter_vs_movie_custom_key",
                shoot_mode="Movie",
                ael_w_shutter="Auto",
                movie_ael_custom_key=ck,
            )
            self.assertTrue(r_ck.allowed)
            self.assertEqual(r_ck.movie_ael_custom_key, ck)

    def test_22_85a_fx3_g96_exposure_step_persistence_erratum_and_initialize(self) -> None:
        # Wave-75 G96 erratum: [Exposure step] (0.3EV / 0.5EV) & [AEL w/ Shutter]
        # are Not available under [Camera Settings Reset] and revert only on [Initialize],
        # whereas Metering Mode, Face Priority, and Spot Metering Point ARE Resettable.
        r_rst = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            metering_mode="Highlight",
            face_priority_requested=False,
            spot_metering_point="Focus Point Link",
            ael_w_shutter="Off",
            exposure_step="0.5EV",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertTrue(r_rst.g96_expstep_erratum_reconciled)
        self.assertTrue(r_rst.resettable_items_reverted)
        self.assertTrue(r_rst.reset_resistant_items_preserved)
        self.assertFalse(r_rst.initialize_reverted)
        self.assertEqual(r_rst.metering_mode, "Multi")
        self.assertTrue(r_rst.face_priority_in_multi)
        self.assertEqual(r_rst.spot_metering_point, "Center")
        self.assertEqual(r_rst.exposure_step, "0.5EV")
        self.assertEqual(r_rst.ael_w_shutter, "Off")

        r_init = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            ael_w_shutter="Off",
            exposure_step="0.5EV",
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertTrue(r_init.initialize_reverted)
        self.assertEqual(r_init.exposure_step, "0.3EV")
        self.assertEqual(r_init.ael_w_shutter, "Auto")

    def test_23_85a_fx3_shutter_angle_immune_and_cine_ei_mm_locked(self) -> None:
        for step in ("0.3EV", "0.5EV"):
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_exposure_step_g96_erratum_and_cine_ei",
                exposure_step=step,
                shutter_angle_deg=172.8,
                log_shooting_mode="Cine EI",
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.shutter_angle_drift_events, 0)
            self.assertTrue(r.cine_ei_mm_locked_to_base_iso)

        r_flex = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            exposure_step="0.5EV",
            log_shooting_mode="Flexible ISO",
        )
        self.assertTrue(r_flex.allowed)
        self.assertFalse(r_flex.cine_ei_mm_locked_to_base_iso)

    def test_24_85a_fx3_invalid_exposure_step_and_angle_einval(self) -> None:
        r_step = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            exposure_step="1.0EV",
        )
        self.assertFalse(r_step.allowed)
        self.assertEqual(r_step.errno, p372.EINVAL_ERRNO)

        r_ang = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            shutter_angle_deg=361.0,
        )
        self.assertFalse(r_ang.allowed)
        self.assertEqual(r_ang.errno, p372.EINVAL_ERRNO)

    def test_25_85a_fx6_ae_level_25_exact_steps_disproves_2ev_rumor(self) -> None:
        self.assertEqual(len(p372.FX6_AE_LEVEL_STEPS), 25)
        self.assertEqual(p372.FX6_AE_LEVEL_MIN, -3.0)
        self.assertEqual(p372.FX6_AE_LEVEL_MAX, 3.0)
        for lvl in p372.FX6_AE_LEVEL_STEPS:
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx6_auto_exposure_25step_and_detect_window",
                body_model=p372.BODY_MODEL_FX6,
                fx6_ae_level=lvl,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_ae_level_steps_count, 25)
            self.assertTrue(r.fx6_2ev_rumor_disproved)

    def test_26_85a_fx6_ae_level_non_025_and_oob_rejected(self) -> None:
        for bad_lvl in (-3.25, -2.1, 0.3, 3.25):
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx6_auto_exposure_25step_and_detect_window",
                body_model=p372.BODY_MODEL_FX6,
                fx6_ae_level=bad_lvl,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EINVAL_ERRNO)

    def test_27_85a_fx6_ae_modes_speed_and_detect_windows(self) -> None:
        for mode in p372.FX6_AE_MODES:
            for win in p372.FX6_AE_DETECT_WINDOWS:
                r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                    operation="fx6_auto_exposure_25step_and_detect_window",
                    body_model=p372.BODY_MODEL_FX6,
                    fx6_ae_mode=mode,
                    fx6_ae_speed=-99 if win == "1" else 99,
                    fx6_detect_window=win,
                )
                self.assertTrue(r.allowed)
                self.assertEqual(r.fx6_ae_mode, mode)
                self.assertEqual(r.fx6_detect_window, win)

        r_spd = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx6_auto_exposure_25step_and_detect_window",
            body_model=p372.BODY_MODEL_FX6,
            fx6_ae_speed=100,
        )
        self.assertFalse(r_spd.allowed)
        self.assertEqual(r_spd.errno, p372.EINVAL_ERRNO)

    def test_28_85a_cross_body_rejections_eopnotsupp(self) -> None:
        r1 = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_metering_6mode_and_ciz_lock",
            body_model=p372.BODY_MODEL_FX6,
        )
        r2 = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx6_auto_exposure_25step_and_detect_window",
            body_model=p372.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p372.EOPNOTSUPP_ERRNO)

    def test_29_85a_invalid_dispatch_raises_stage85_error(self) -> None:
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85a_metering_ael_expstep_and_fx6_ae(operation="bad_85a")
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_metering_6mode_and_ciz_lock", body_model="FX9"
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_metering_6mode_and_ciz_lock", shoot_mode="Playback"
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_metering_6mode_and_ciz_lock", desqueeze_display="1.8x"
            )

    def test_30_85a_orchestrator_metrics_and_zero_writes(self) -> None:
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        s85a = rep["submodel_85a_metering_ael_expstep_fx6_ae"]
        self.assertTrue(s85a["passed"])
        self.assertEqual(s85a["fx3_metering_modes_count"], 6)
        self.assertEqual(
            s85a["fx3_face_priority_symbol"],
            "BKID_APP_setting_face_detection_in_multi",
        )
        self.assertTrue(s85a["fx3_exposure_step_g96_erratum_reconciled"])
        self.assertTrue(s85a["fx3_shutter_angle_immune_to_exp_step"])
        self.assertEqual(s85a["fx6_ae_level_steps_count"], 25)
        self.assertEqual(s85a["fx6_ae_level_range"], [-3.0, 3.0])
        self.assertTrue(s85a["fx6_2ev_rumor_disproved"])

    def test_31_85a_invalid_spot_and_ael_enums_einval(self) -> None:
        r_sp = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_spot_metering_point_coupling",
            metering_mode="Spot: Large",
            spot_metering_point="Tracking",
        )
        self.assertEqual(r_sp.errno, p372.EINVAL_ERRNO)

        r_ael = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_ael_w_shutter_vs_movie_custom_key",
            ael_w_shutter="Always",
        )
        self.assertEqual(r_ael.errno, p372.EINVAL_ERRNO)

        r_ck = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_ael_w_shutter_vs_movie_custom_key",
            movie_ael_custom_key="BOGUS_KEY",
        )
        self.assertEqual(r_ck.errno, p372.EINVAL_ERRNO)

    def test_32_85a_fx6_invalid_ae_mode_and_detect_window_einval(self) -> None:
        r_m = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx6_auto_exposure_25step_and_detect_window",
            body_model=p372.BODY_MODEL_FX6,
            fx6_ae_mode="Multi",
        )
        self.assertEqual(r_m.errno, p372.EINVAL_ERRNO)

        r_w = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx6_auto_exposure_25step_and_detect_window",
            body_model=p372.BODY_MODEL_FX6,
            fx6_detect_window="7",
        )
        self.assertEqual(r_w.errno, p372.EINVAL_ERRNO)

    def test_33_85a_cine_ei_quick_also_locks_mm_to_base_iso(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            log_shooting_mode="Cine EI Quick",
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.cine_ei_mm_locked_to_base_iso)

    def test_34_85a_zero_writes_and_zero_leak(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            exposure_step="0.5EV",
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_35_85a_spot_focus_point_link_active_under_spot_m_in_both_spots(self) -> None:
        for fa in ("Spot: S", "Spot: M", "Spot: L", "Expand Spot"):
            r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
                operation="fx3_spot_metering_point_coupling",
                metering_mode="Spot: Large",
                spot_metering_point="Focus Point Link",
                focus_area=fa,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.spot_metering_point, "Focus Point Link")

    def test_36_85a_face_priority_off_allowed_under_desqueeze(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_face_priority_multi_locks",
            metering_mode="Multi",
            desqueeze_display="1.6x",
            face_priority_requested=False,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.face_priority_in_multi)

    def test_37_85a_shutter_angle_immune_flag_and_zero_drift(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_exposure_step_g96_erratum_and_cine_ei",
            exposure_step="0.5EV",
            shutter_angle_deg=90.0,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.shutter_angle_drift_events, 0)

    def test_38_85a_movie_ael_w_shutter_auto_accepted_for_movie_custom_key_flow(self) -> None:
        r = p372.simulate_85a_metering_ael_expstep_and_fx6_ae(
            operation="fx3_ael_w_shutter_vs_movie_custom_key",
            shoot_mode="S&Q",
            ael_w_shutter="Auto",
            movie_ael_custom_key="Spot AEL toggle",
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.movie_ael_custom_key, "Spot AEL toggle")

    # =========================================================================
    # Tests 39..60: Sub-Model 85B — Picture Profile PP1..11 Dual-Immune vs
    #               PPLUT1..4 Resettable, User1..16 .cube & MP4 Embed LUT File
    # =========================================================================

    def test_39_85b_fx3_picture_profile_default_pp11_and_16_total_modes(self) -> None:
        self.assertEqual(p372.FX3_PICTURE_PROFILE_DEFAULT, "PP11")
        self.assertEqual(len(p372.FX3_PP_STD_SLOTS), 11)
        self.assertEqual(len(p372.FX3_PPLUT_SLOTS), 4)
        self.assertEqual(len(p372.FX3_PICTURE_PROFILES), 16)
        for pp in p372.FX3_PICTURE_PROFILES:
            r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
                shoot_mode="Movie",
                picture_profile=pp,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.picture_profile, pp)

    def test_40_85b_fx3_pplut1_to_4_movie_only_and_hdmi_1080p_downshift(self) -> None:
        for pplut in p372.FX3_PPLUT_SLOTS:
            r_mv = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
                shoot_mode="Movie",
                picture_profile=pplut,
            )
            self.assertTrue(r_mv.allowed)
            self.assertTrue(r_mv.pplut_baking_active)
            self.assertEqual(r_mv.hdmi_output_resolution, "1080p")

            r_st = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
                shoot_mode="Still",
                picture_profile=pplut,
            )
            self.assertFalse(r_st.allowed)
            self.assertEqual(r_st.errno, p372.EOPNOTSUPP_ERRNO)

        # Exceptions to 1080p clamp: Off (HDMI Only) or HDMI RAW Output = On
        r_hdmi_only = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
            picture_profile="PPLUT1",
            hdmi_only_rec_media_off=True,
        )
        self.assertTrue(r_hdmi_only.allowed)
        self.assertEqual(r_hdmi_only.hdmi_output_resolution, "2160p")

        r_raw = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
            picture_profile="PPLUT2",
            hdmi_raw_output_on=True,
        )
        self.assertTrue(r_raw.allowed)
        self.assertEqual(r_raw.hdmi_output_resolution, "2160p")

    def test_41_85b_fx3_log_shooting_mutex_forces_pp_off(self) -> None:
        r_blk = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
            picture_profile="PP11",
            log_shooting_enabled=True,
        )
        self.assertFalse(r_blk.allowed)
        self.assertEqual(r_blk.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_blk.picture_profile, "Off")

        r_off = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
            picture_profile="Off",
            log_shooting_enabled=True,
        )
        self.assertTrue(r_off.allowed)

    def test_42_85b_fx3_asymmetric_reset_and_initialize_split_law(self) -> None:
        # Reset reverts active PP -> PP11 and reverts PPLUT1..4, while PP1..11 custom
        # params & DiffSet Still/Mv PP checkbox survive Reset AND Initialize!
        r_rst = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_reset_vs_initialize_asymmetric_split",
            picture_profile="PPLUT3",
            pp1_to_pp11_custom_edited=True,
            diff_set_still_mv_pp_checked=True,
            user_lut_registered=True,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertEqual(r_rst.picture_profile, "PP11")
        self.assertTrue(r_rst.pplut1_to_4_reverted)
        self.assertTrue(r_rst.pp1_to_pp11_custom_preserved_across_reset_and_init)
        self.assertTrue(r_rst.diff_set_pp_checkbox_preserved_across_reset_and_init)
        self.assertTrue(r_rst.user_luts_preserved_across_reset)
        self.assertFalse(r_rst.user_luts_cleared_on_init_or_delete_all)

        r_init = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_reset_vs_initialize_asymmetric_split",
            picture_profile="PP5",
            pp1_to_pp11_custom_edited=True,
            diff_set_still_mv_pp_checked=True,
            user_lut_registered=True,
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertEqual(r_init.picture_profile, "PP11")
        self.assertTrue(r_init.pplut1_to_4_reverted)
        self.assertTrue(r_init.pp1_to_pp11_custom_preserved_across_reset_and_init)
        self.assertTrue(r_init.diff_set_pp_checkbox_preserved_across_reset_and_init)
        self.assertTrue(r_init.user_luts_cleared_on_init_or_delete_all)

    def test_43_85b_fx3_user1_16_cube_17_33pt_63chars_sd_vs_cfexpress_dirs(self) -> None:
        self.assertEqual(p372.FX3_USER_LUT_MAX_SLOTS, 16)
        self.assertEqual(p372.FX3_SD_LUT_DIR, "/Private/Sony/PRO/LUT")
        self.assertEqual(p372.FX3_CFEX_LUT_DIR, "/Sony/PRO/LUT")
        for grid in (17, 33):
            r_sd = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_manage_user_luts_import_cube_and_delete",
                card_type="SDXC",
                user_lut_slot="User1",
                cube_grid_points=grid,
                cube_filename="A" * 58 + ".cube",
            )
            self.assertTrue(r_sd.allowed)
            self.assertEqual(r_sd.cube_filename_length, 63)
            self.assertEqual(r_sd.lut_import_directory, "/Private/Sony/PRO/LUT")

            r_cf = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_manage_user_luts_import_cube_and_delete",
                card_type="CFexpress",
                user_lut_slot="User16",
                cube_grid_points=grid,
                cube_filename="LUT_V702.cube",
            )
            self.assertTrue(r_cf.allowed)
            self.assertEqual(r_cf.lut_import_directory, "/Sony/PRO/LUT")

    def test_44_85b_fx3_rejects_64char_cube_and_65pt_cube_einval(self) -> None:
        r_64 = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            cube_filename="A" * 59 + ".cube",
        )
        self.assertFalse(r_64.allowed)
        self.assertEqual(r_64.errno, p372.EINVAL_ERRNO)

        r_65pt = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            cube_grid_points=65,
        )
        self.assertFalse(r_65pt.allowed)
        self.assertEqual(r_65pt.errno, p372.EINVAL_ERRNO)

        r_ext = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            cube_filename="bad.3dl",
        )
        self.assertFalse(r_ext.allowed)
        self.assertEqual(r_ext.errno, p372.EINVAL_ERRNO)

    def test_45_85b_fx3_user_luts_survive_reset_and_clear_on_delete_all(self) -> None:
        r_rst = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            select_lut="User3",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertEqual(r_rst.select_lut, "s709")
        self.assertTrue(r_rst.user_luts_preserved_across_reset)
        self.assertFalse(r_rst.user_luts_cleared_on_init_or_delete_all)

        r_del = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            delete_all_user_luts_triggered=True,
        )
        self.assertTrue(r_del.allowed)
        self.assertTrue(r_del.user_luts_cleared_on_init_or_delete_all)

    def test_46_85b_fx3_embed_lut_mp4_only_zero_mxf_zero_sidecar_and_sdhc_lock(self) -> None:
        for card in ("SD", "SDHC"):
            r_blk = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
                card_type=card,
                embed_lut_requested=True,
            )
            self.assertFalse(r_blk.allowed)
            self.assertEqual(r_blk.errno, p372.EOPNOTSUPP_ERRNO)
            self.assertFalse(r_blk.embed_lut_file)

        for card in ("SDXC", "CFexpress"):
            r_ok = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
                card_type=card,
                select_lut="User1",
                embed_lut_requested=True,
            )
            self.assertTrue(r_ok.allowed)
            self.assertTrue(r_ok.embed_lut_file)
            self.assertEqual(r_ok.embed_container_format, "MP4")
            self.assertEqual(r_ok.fx3_mxf_hits, 0)
            self.assertEqual(r_ok.fx3_cube_sidecar_files, 0)

    def test_47_85b_fx6_base_look_16axis_multi_matrix_4bus_mlut_mxf(self) -> None:
        for look in ("S-Cinetone", "709tone", "S-Log3", "User1"):
            r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx6_base_look_multimatrix_mlut_mxf_embed",
                body_model=p372.BODY_MODEL_FX6,
                fx6_base_look=look,
                fx6_multi_matrix_hue=-99,
                fx6_multi_matrix_sat=99,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_base_look, look)
            self.assertEqual(r.fx6_multi_matrix_axes, 16)
            self.assertEqual(r.fx6_mlut_buses_count, 4)
            self.assertEqual(r.embed_container_format, "MXF")

        r_oob = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx6_base_look_multimatrix_mlut_mxf_embed",
            body_model=p372.BODY_MODEL_FX6,
            fx6_multi_matrix_hue=100,
        )
        self.assertFalse(r_oob.allowed)
        self.assertEqual(r_oob.errno, p372.EINVAL_ERRNO)

    def test_48_85b_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
            body_model=p372.BODY_MODEL_FX6,
        )
        r2 = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx6_base_look_multimatrix_mlut_mxf_embed",
            body_model=p372.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p372.EOPNOTSUPP_ERRNO)

    def test_49_85b_invalid_dispatch_raises_stage85_error(self) -> None:
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(operation="bad_85b")
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex", card_type="XQD"
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex", media_slot="Slot 9"
            )

    def test_50_85b_orchestrator_metrics_and_elf_typo_symbol(self) -> None:
        self.assertEqual(
            p372.FX3_PPLUT_ELF_TYPO_SYMBOL,
            "BKID_APP_MR_setting_pplut1_link_uset_lut",
        )
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        s85b = rep["submodel_85b_pp_pplut_userlut_embed_fx6_paint"]
        self.assertTrue(s85b["passed"])
        self.assertEqual(s85b["fx3_pp_default"], "PP11")
        self.assertEqual(s85b["fx3_pplut_slots_count"], 4)
        self.assertTrue(s85b["fx3_pp1_11_dual_immune"])
        self.assertEqual(s85b["fx3_user_lut_slots_count"], 16)
        self.assertEqual(s85b["fx3_embed_container"], "MP4")
        self.assertEqual(s85b["fx3_mxf_hits"], 0)
        self.assertEqual(s85b["fx3_cube_sidecar_files"], 0)
        self.assertEqual(s85b["fx6_multi_matrix_axes"], 16)
        self.assertEqual(s85b["fx6_mlut_buses_count"], 4)

    def test_51_85b_invalid_pp_and_user_slot_and_select_lut_einval(self) -> None:
        r_pp = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
            picture_profile="PP12",
        )
        self.assertEqual(r_pp.errno, p372.EINVAL_ERRNO)

        r_usr = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
            user_lut_slot="User17",
        )
        self.assertEqual(r_usr.errno, p372.EINVAL_ERRNO)

        r_sel = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
            select_lut="PPLUT9",
        )
        self.assertEqual(r_sel.errno, p372.EINVAL_ERRNO)

    def test_52_85b_fx3_sd_and_sdhc_allow_embed_lut_off(self) -> None:
        r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
            card_type="SDHC",
            embed_lut_requested=False,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.embed_lut_file)

    def test_53_85b_fx6_invalid_base_look_einval(self) -> None:
        r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx6_base_look_multimatrix_mlut_mxf_embed",
            body_model=p372.BODY_MODEL_FX6,
            fx6_base_look="PPLUT1",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p372.EINVAL_ERRNO)

    def test_54_85b_zero_writes_and_zero_leak(self) -> None:
        r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx3_manage_user_luts_import_cube_and_delete",
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_55_85b_fx6_user_lut_ui_16_vs_50_buffer_constants(self) -> None:
        self.assertEqual(p372.FX6_USER_LUT_UI_SLOTS, 16)
        self.assertEqual(p372.FX6_USER_LUT_BUFFER_SLOTS, 50)
        self.assertFalse(p372.FX3_HAS_MXF_CONTAINER)

    def test_56_85b_fx3_embed_lut_menu_path_constant(self) -> None:
        self.assertEqual(
            p372.FX3_EMBED_LUT_MENU_PATH,
            "Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]",
        )

    def test_57_85b_fx3_pp11_still_and_movie_allowed_2160p(self) -> None:
        for sm in ("Still", "Movie"):
            r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_pp_pp11_pplut14_hdmi_and_log_mutex",
                shoot_mode=sm,
                picture_profile="PP11",
            )
            self.assertTrue(r.allowed)
            self.assertFalse(r.pplut_baking_active)
            self.assertEqual(r.hdmi_output_resolution, "2160p")

    def test_58_85b_fx3_select_lut_builtins_all_accepted(self) -> None:
        for sel in p372.FX3_SELECT_LUT_BUILTINS:
            r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
                operation="fx3_embed_lut_mp4_vs_sd_sdhc_lock",
                select_lut=sel,
                card_type="CFexpress",
                embed_lut_requested=True,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.select_lut, sel)

    def test_59_85b_fx6_4_mlut_buses_constant(self) -> None:
        self.assertEqual(
            p372.FX6_MLUT_BUSES,
            ("Internal Rec.", "SDI/HDMI", "LCD/VF", "Proxy/Stream"),
        )

    def test_60_85b_fx6_user_lut_slots_import_also_supported_on_fx6_base_look(self) -> None:
        r = p372.simulate_85b_pp_pplut_userlut_embed_and_fx6_paint(
            operation="fx6_base_look_multimatrix_mlut_mxf_embed",
            body_model=p372.BODY_MODEL_FX6,
            fx6_base_look="User16",
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.user_lut_slots_count, 16)

    # =========================================================================
    # Tests 61..80: Sub-Model 85C — 5-Axis IBIS SteadyShot Active 1.1x, Exact
    #               47-Entry Focal Table (8..1000mm), Catalyst Gyro vs FX6 OSS
    # =========================================================================

    def test_61_85c_fx3_movie_steadyshot_active_1_1x_and_distortion_comp_auto(self) -> None:
        r_act = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            shoot_mode="Movie",
            steadyshot_mode="Active",
            distortion_comp="Auto",
            frame_rate_fps=59.94,
        )
        self.assertTrue(r_act.allowed)
        self.assertAlmostEqual(r_act.steadyshot_crop_factor, 1.1, places=6)
        self.assertTrue(r_act.distortion_comp_forced_auto)

        r_dist_off = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            shoot_mode="Movie",
            steadyshot_mode="Active",
            distortion_comp="Off",
        )
        self.assertFalse(r_dist_off.allowed)
        self.assertEqual(r_dist_off.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_dist_off.distortion_comp_forced_auto)

    def test_62_85c_fx3_active_4_cutoffs_100p_sq100_hdmi_raw_and_desqueeze(self) -> None:
        for fps in (100.0, 119.88):
            r_hfr = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_crop_distortion_and_4locks",
                shoot_mode="Movie",
                steadyshot_mode="Active",
                frame_rate_fps=fps,
            )
            self.assertFalse(r_hfr.allowed)
            self.assertEqual(r_hfr.errno, p372.EOPNOTSUPP_ERRNO)

        r_sq = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            shoot_mode="S&Q",
            steadyshot_mode="Active",
            frame_rate_fps=100.0,
        )
        self.assertFalse(r_sq.allowed)
        self.assertEqual(r_sq.errno, p372.EOPNOTSUPP_ERRNO)

        r_raw = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            steadyshot_mode="Active",
            hdmi_raw_output_on=True,
        )
        self.assertFalse(r_raw.allowed)
        self.assertEqual(r_raw.errno, p372.EOPNOTSUPP_ERRNO)

        for desq in ("1.3x", "1.5x", "1.6x", "2.0x"):
            r_desq = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_crop_distortion_and_4locks",
                steadyshot_mode="Active",
                desqueeze_display=desq,
            )
            self.assertFalse(r_desq.allowed)
            self.assertEqual(r_desq.errno, p372.EOPNOTSUPP_ERRNO)

    def test_63_85c_fx3_still_steadyshot_on_off_only_rejects_active_standard(self) -> None:
        for st_m in ("On", "Off"):
            r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_crop_distortion_and_4locks",
                shoot_mode="Still",
                steadyshot_mode=st_m,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.steadyshot_mode, st_m)

        for mv_m in ("Active", "Standard"):
            r_bad = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_active_crop_distortion_and_4locks",
                shoot_mode="Still",
                steadyshot_mode=mv_m,
            )
            self.assertFalse(r_bad.allowed)
            self.assertEqual(r_bad.errno, p372.EOPNOTSUPP_ERRNO)

    def test_64_85c_fx3_exact_47_entry_focal_length_table_and_gaps(self) -> None:
        tbl = p372.FX3_47_FOCAL_LENGTH_TABLE_MM
        self.assertEqual(len(tbl), 47)
        self.assertEqual(tbl[0], 8)
        self.assertEqual(tbl[-1], 1000)
        self.assertEqual(p372.FX3_FOCAL_LENGTH_DEFAULT_MM, 8)
        self.assertEqual(list(tbl), sorted(set(tbl)))

        for fl in tbl:
            r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_47_focal_table_and_reset",
                steadyshot_adjust="Manual",
                steadyshot_focal_length_mm=fl,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.steadyshot_focal_length_mm, fl)
            self.assertEqual(r.focal_length_table_count, 47)

        for non_table_fl in (7, 22, 23, 27, 38, 72, 110, 550, 900, 1200):
            r_gap = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_47_focal_table_and_reset",
                steadyshot_adjust="Manual",
                steadyshot_focal_length_mm=non_table_fl,
            )
            self.assertFalse(r_gap.allowed)
            self.assertEqual(r_gap.errno, p372.EINVAL_ERRNO)

    def test_65_85c_fx3_all_4_steadyshot_items_revert_under_camera_settings_reset(self) -> None:
        r_rst = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_47_focal_table_and_reset",
            shoot_mode="Movie",
            steadyshot_mode="Active",
            steadyshot_adjust="Manual",
            steadyshot_focal_length_mm=50,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertTrue(r_rst.resettable_all_4_reverted)
        self.assertEqual(r_rst.steadyshot_mode, "Standard")
        self.assertEqual(r_rst.steadyshot_adjust, "Auto")
        self.assertEqual(r_rst.steadyshot_focal_length_mm, 8)

    def test_66_85c_fx3_dormant_alpha_steadyshot_modes_rejected(self) -> None:
        for dorm in p372.FX3_DORMANT_STEADYSHOT_MODES:
            r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_dormant_alpha_steadyshot_rejected",
                steadyshot_mode=dorm,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.dormant_steadyshot_exposed_events, 0)

    def test_67_85c_fx3_catalyst_gyro_matrix(self) -> None:
        # Recorded only with Off or Active + E-mount electronic lens, absent in Standard/120p/S&Q
        for ss in ("Off", "Active"):
            r_ok = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_catalyst_gyro_metadata_matrix",
                shoot_mode="Movie",
                steadyshot_mode=ss,
                frame_rate_fps=23.98,
                emount_electronic_lens=True,
            )
            self.assertTrue(r_ok.allowed)
            self.assertTrue(r_ok.catalyst_gyro_metadata_present)

        r_std = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_metadata_matrix",
            shoot_mode="Movie",
            steadyshot_mode="Standard",
            frame_rate_fps=23.98,
            emount_electronic_lens=True,
        )
        self.assertTrue(r_std.allowed)
        self.assertFalse(r_std.catalyst_gyro_metadata_present)

        r_120p = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_metadata_matrix",
            shoot_mode="Movie",
            steadyshot_mode="Off",
            frame_rate_fps=119.88,
            emount_electronic_lens=True,
        )
        self.assertTrue(r_120p.allowed)
        self.assertFalse(r_120p.catalyst_gyro_metadata_present)

        r_sq = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_metadata_matrix",
            shoot_mode="S&Q",
            steadyshot_mode="Off",
            frame_rate_fps=23.98,
            emount_electronic_lens=True,
        )
        self.assertTrue(r_sq.allowed)
        self.assertFalse(r_sq.catalyst_gyro_metadata_present)

        r_manual_lens = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_metadata_matrix",
            shoot_mode="Movie",
            steadyshot_mode="Off",
            frame_rate_fps=23.98,
            emount_electronic_lens=False,
        )
        self.assertTrue(r_manual_lens.allowed)
        self.assertFalse(r_manual_lens.catalyst_gyro_metadata_present)

    def test_68_85c_fx6_zero_physical_ibis_oss_only_and_dormant_focal_rejected(self) -> None:
        self.assertFalse(p372.FX6_HAS_PHYSICAL_IBIS)
        self.assertEqual(
            p372.FX6_STEADYSHOT_ERR_SYMBOL,
            "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED",
        )
        for oss in p372.FX6_OSS_MODES:
            r_oss = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
                body_model=p372.BODY_MODEL_FX6,
                fx6_oss_mode=oss,
            )
            self.assertTrue(r_oss.allowed)
            self.assertFalse(r_oss.fx6_has_physical_ibis)
            self.assertEqual(r_oss.fx6_oss_mode, oss)

        r_act = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX6,
            steadyshot_mode="Active",
        )
        self.assertFalse(r_act.allowed)
        self.assertEqual(r_act.errno, p372.EOPNOTSUPP_ERRNO)

        r_fl = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX6,
            steadyshot_adjust="Manual",
            steadyshot_focal_length_mm=50,
        )
        self.assertFalse(r_fl.allowed)
        self.assertEqual(r_fl.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_fl.fx6_dormant_focal_exposed_events, 0)

    def test_69_85c_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_47_focal_table_and_reset",
            body_model=p372.BODY_MODEL_FX6,
        )
        r2 = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p372.EOPNOTSUPP_ERRNO)

    def test_70_85c_invalid_dispatch_raises_stage85_error(self) -> None:
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(operation="bad_85c")
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_47_focal_table_and_reset", body_model="A1"
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
                operation="fx3_steadyshot_47_focal_table_and_reset",
                desqueeze_display="1.33x",
            )

    def test_71_85c_invalid_adjust_and_oss_enums_einval(self) -> None:
        r_adj = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_47_focal_table_and_reset",
            steadyshot_adjust="SemiAuto",
        )
        self.assertEqual(r_adj.errno, p372.EINVAL_ERRNO)

        r_oss = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX6,
            fx6_oss_mode="Active",
        )
        self.assertEqual(r_oss.errno, p372.EINVAL_ERRNO)

    def test_72_85c_orchestrator_metrics_alignment(self) -> None:
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        s85c = rep["submodel_85c_ibis47_active_catalyst_fx6_oss"]
        self.assertTrue(s85c["passed"])
        self.assertEqual(s85c["fx3_focal_table_entries_count"], 47)
        self.assertAlmostEqual(s85c["fx3_active_crop_factor"], 1.1, places=6)
        self.assertEqual(s85c["fx3_dormant_steadyshot_exposed_events"], 0)
        self.assertFalse(s85c["fx6_has_physical_ibis"])
        self.assertEqual(s85c["fx6_dormant_focal_exposed_events"], 0)

    def test_73_85c_zero_writes_and_zero_leak(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            steadyshot_mode="Active",
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_74_85c_fx3_dormant_mode_also_rejected_in_crop_operation(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            steadyshot_mode="Dynamic active",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p372.EOPNOTSUPP_ERRNO)

    def test_75_85c_fx3_dormant_non_dormant_mode_accepted_in_check(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_dormant_alpha_steadyshot_rejected",
            steadyshot_mode="Standard",
        )
        self.assertTrue(r.allowed)

    def test_76_85c_fx3_active_allowed_up_to_59_94p_with_sq(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            shoot_mode="S&Q",
            steadyshot_mode="Active",
            frame_rate_fps=50.0,
        )
        self.assertTrue(r.allowed)
        self.assertAlmostEqual(r.steadyshot_crop_factor, 1.1, places=6)

    def test_77_85c_fx3_catalyst_gyro_rejects_still_steadyshot_enum(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_catalyst_gyro_metadata_matrix",
            steadyshot_mode="On",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p372.EOPNOTSUPP_ERRNO)

    def test_78_85c_fx3_active_at_exactly_60p_allowed(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_active_crop_distortion_and_4locks",
            steadyshot_mode="Active",
            frame_rate_fps=60.0,
        )
        self.assertTrue(r.allowed)

    def test_79_85c_fx3_still_reset_reverts_steadyshot_to_on(self) -> None:
        r = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx3_steadyshot_47_focal_table_and_reset",
            shoot_mode="Still",
            steadyshot_mode="Off",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.steadyshot_mode, "On")

    def test_80_85c_fx6_gyro_recorded_only_when_oss_off(self) -> None:
        r_off = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX6,
            fx6_oss_mode="Off",
        )
        self.assertTrue(r_off.allowed)
        self.assertTrue(r_off.catalyst_gyro_metadata_present)

        r_on = p372.simulate_85c_ibis47_active_catalyst_and_fx6_oss(
            operation="fx6_zero_ibis_oss_and_dormant_focal_rejected",
            body_model=p372.BODY_MODEL_FX6,
            fx6_oss_mode="On",
        )
        self.assertTrue(r_on.allowed)
        self.assertFalse(r_on.catalyst_gyro_metadata_present)

    # =========================================================================
    # Tests 81..96: Sub-Model 85D — Zero-Write Playback Viewing vs Still DCF /
    #               Movie Cam ID+Reel# 17-Char & 37-Char Title Slot 1 EROFS=30
    # =========================================================================

    def test_81_85d_fx3_playback_5items_zero_write_and_reset_resistant(self) -> None:
        self.assertEqual(
            p372.FX3_DISPLAY_ROTATION_ELF_TYPO_SYMBOL,
            "BKID_APP_setting_display_rotatiton",
        )
        self.assertEqual(p372.FX3_PB_IMAGE_INDEX_MODES, ("9 Images", "25 Images"))
        for idx in p372.FX3_PB_IMAGE_INDEX_MODES:
            for rot in p372.FX3_DISPLAY_ROTATION_MODES:
                r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                    operation="fx3_playback_5items_zero_write_and_reset_immune",
                    pb_image_index=idx,
                    display_rotation=rot,
                    focus_frame_display=True,
                    cont_pb_for_interval=True,
                    play_speed_for_interval=9,
                    camera_settings_reset_triggered=True,
                )
                self.assertTrue(r.allowed)
                self.assertTrue(r.pb_reset_immune_preserved)
                self.assertEqual(r.pb_image_index, idx)
                self.assertEqual(r.display_rotation, rot)
                self.assertEqual(r.play_speed_for_interval, 9)
                self.assertEqual(r.slot1_sector_writes, 0)
                self.assertEqual(r.slot1_data_sector_writes, 0)
                self.assertFalse(r.slot1_avf_info_mutated)
                self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_82_85d_fx3_dormant_12_30_images_and_inbody_interval_mux_rejected(self) -> None:
        for dorm in p372.FX3_PB_DORMANT_IMAGE_INDEX_MODES:
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_playback_5items_zero_write_and_reset_immune",
                pb_image_index=dorm,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EOPNOTSUPP_ERRNO)

        r_mux = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_playback_5items_zero_write_and_reset_immune",
            inbody_interval_mux_requested=True,
        )
        self.assertFalse(r_mux.allowed)
        self.assertEqual(r_mux.errno, p372.EOPNOTSUPP_ERRNO)

        for oob_spd in (0, 10):
            r_spd = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_playback_5items_zero_write_and_reset_immune",
                play_speed_for_interval=oob_spd,
            )
            self.assertFalse(r_spd.allowed)
            self.assertEqual(r_spd.errno, p372.EINVAL_ERRNO)

    def test_83_85d_fx3_still_dcf_4000_cap_and_date_form_select_rec_folder_lock(self) -> None:
        r_ok = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_still_dcf_folder_and_4000_cap",
            still_folder_form="Standard Form",
            still_files_in_folder=4000,
        )
        self.assertTrue(r_ok.allowed)

        r_4001 = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_still_dcf_folder_and_4000_cap",
            still_folder_form="Standard Form",
            still_files_in_folder=4001,
        )
        self.assertFalse(r_4001.allowed)
        self.assertEqual(r_4001.errno, p372.EINVAL_ERRNO)

        r_date_sel = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_still_dcf_folder_and_4000_cap",
            still_folder_form="Date Form",
            select_rec_folder_requested=True,
        )
        self.assertFalse(r_date_sel.allowed)
        self.assertEqual(r_date_sel.errno, p372.EOPNOTSUPP_ERRNO)

    def test_84_85d_fx3_movie_camid_reel_17char_stem_and_c999_d001_rollover(self) -> None:
        r_std = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
            camera_id="A",
            reel_num=1,
            camera_pos="C",
            file_num=1,
            yymmdd="230101",
            rand2="AB",
        )
        self.assertTrue(r_std.allowed)
        self.assertEqual(r_std.generated_clip_stem, "A001C001_230101AB")
        self.assertEqual(r_std.generated_stem_length, 17)
        self.assertFalse(r_std.camera_position_menu_mutated)

        r_roll = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
            camera_id="A",
            reel_num=1,
            camera_pos="C",
            file_num=1000,
            yymmdd="230101",
            rand2="AB",
        )
        self.assertTrue(r_roll.allowed)
        self.assertEqual(r_roll.generated_clip_stem, "A001D001_230101AB")
        self.assertEqual(r_roll.generated_stem_length, 17)
        self.assertFalse(r_roll.camera_position_menu_mutated)

    def test_85_85d_fx3_sdhc_locks_movie_file_name_format_to_standard(self) -> None:
        for fmt in ("Cam ID + Reel#", "Title", "Date + Title", "Title + Date"):
            r_blk = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
                card_type="SDHC",
                movie_file_name_format=fmt,
            )
            self.assertFalse(r_blk.allowed)
            self.assertEqual(r_blk.errno, p372.EOPNOTSUPP_ERRNO)
            self.assertEqual(r_blk.movie_file_name_format, "Standard")

        r_ok = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
            card_type="SDHC",
            movie_file_name_format="Standard",
        )
        self.assertTrue(r_ok.allowed)

    def test_86_85d_fx3_title_name_37char_boundary_separated_from_17char_camid(self) -> None:
        self.assertEqual(p372.FX3_TITLE_NAME_DEFAULT, "C")
        self.assertEqual(p372.FX3_TITLE_NAME_MAX_CHARS, 37)
        self.assertEqual(p372.FX3_CAMID_REEL_STEM_LEN, 17)

        r_37 = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_movie_title_37char_settings_boundary",
            title_name="X" * 37,
        )
        self.assertTrue(r_37.allowed)
        self.assertEqual(r_37.title_name_length, 37)

        for bad_t in ("", "X" * 38):
            r_bad = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_movie_title_37char_settings_boundary",
                title_name=bad_t,
            )
            self.assertFalse(r_bad.allowed)
            self.assertEqual(r_bad.errno, p372.EINVAL_ERRNO)

    def test_87_85d_tier0_slot1_erofs_30_blocks_all_4_mutating_ops(self) -> None:
        self.assertEqual(
            p372.FX3_TIER0_SLOT1_MUTATING_OPS,
            (
                "Create New Folder",
                "Forced File No. Reset",
                "Select REC Folder",
                "Series Counter Reset",
            ),
        )
        for act in p372.FX3_TIER0_SLOT1_MUTATING_OPS:
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_tier0_slot1_erofs30_folder_file_firewall",
                media_slot="Slot 1",
                tier0_action=act,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EROFS_ERRNO)
            self.assertTrue(r.tier0_slot1_erofs_enforced)
            self.assertEqual(r.slot1_sector_writes, 0)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)
            self.assertEqual(r.emmc_nflasha_write_count, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_88_85d_slot2_allows_folder_file_ops_with_zero_host_writes(self) -> None:
        for act in p372.FX3_TIER0_SLOT1_MUTATING_OPS:
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_tier0_slot1_erofs30_folder_file_firewall",
                media_slot="Slot 2",
                tier0_action=act,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.slot1_sector_writes, 0)
            self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_89_85d_fx6_clip_name_format_mxf_and_title_prefix_4_to_46(self) -> None:
        self.assertEqual(p372.FX6_TITLE_PREFIX_DEFAULT, "nnn_")
        self.assertEqual(p372.FX6_CLIP_OUTPUT_PATH, "/XDROOT/Clip/*.MXF")
        for fmt in p372.FX6_CLIP_NAME_FORMATS:
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx6_clip_name_format_mxf_and_title_prefix",
                body_model=p372.BODY_MODEL_FX6,
                fx6_clip_name_format=fmt,
                fx6_title_prefix="A" * 46 if fmt == "Title" else "nnn_",
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_clip_output_path, "/XDROOT/Clip/*.MXF")

        for bad_pref in ("abc", "A" * 47):
            r_oob = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx6_clip_name_format_mxf_and_title_prefix",
                body_model=p372.BODY_MODEL_FX6,
                fx6_clip_name_format="Title",
                fx6_title_prefix=bad_pref,
            )
            self.assertFalse(r_oob.allowed)
            self.assertEqual(r_oob.errno, p372.EINVAL_ERRNO)

    def test_90_85d_cross_body_operations_eopnotsupp(self) -> None:
        r1 = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_playback_5items_zero_write_and_reset_immune",
            body_model=p372.BODY_MODEL_FX6,
        )
        r2 = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx6_clip_name_format_mxf_and_title_prefix",
            body_model=p372.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p372.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p372.EOPNOTSUPP_ERRNO)

    def test_91_85d_invalid_dispatch_raises_stage85_error(self) -> None:
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85d_playback_viewing_camid_37title_and_erofs(operation="bad_85d")
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_playback_5items_zero_write_and_reset_immune",
                body_model="FX9",
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_playback_5items_zero_write_and_reset_immune",
                media_slot="Slot 3",
            )
        with self.assertRaises(p372.Stage85Phase372Error):
            p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_playback_5items_zero_write_and_reset_immune",
                card_type="UHS-0",
            )

    def test_92_85d_invalid_camid_pos_reel_and_tier0_action_einval(self) -> None:
        for bad_kw in (
            {"camera_id": "1"},
            {"camera_pos": "X"},
            {"reel_num": 0},
            {"reel_num": 1000},
        ):
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
                **bad_kw,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p372.EINVAL_ERRNO)

        r_act = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_tier0_slot1_erofs30_folder_file_firewall",
            tier0_action="Erase All",
        )
        self.assertEqual(r_act.errno, p372.EINVAL_ERRNO)

    def test_93_85d_camid_l_and_r_rollover_preserves_menu_camera_pos(self) -> None:
        for pos, rolled in (("L", "M"), ("R", "S")):
            r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
                operation="fx3_movie_camid_reel_17char_rollover_and_sdhc_lock",
                camera_id="B",
                reel_num=12,
                camera_pos=pos,
                file_num=1001,
                yymmdd="240501",
                rand2="ZZ",
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.generated_clip_stem, f"B012{rolled}002_240501ZZ")
            self.assertFalse(r.camera_position_menu_mutated)

    def test_94_85d_orchestrator_metrics_alignment(self) -> None:
        rep = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        s85d = rep["submodel_85d_playback_camid_37title_erofs"]
        self.assertTrue(s85d["passed"])
        self.assertEqual(s85d["fx3_pb_image_index_count"], 2)
        self.assertEqual(s85d["fx3_pb_dormant_index_exposed_events"], 0)
        self.assertEqual(
            s85d["fx3_display_rotation_elf_typo_symbol"],
            "BKID_APP_setting_display_rotatiton",
        )
        self.assertEqual(s85d["fx3_camid_reel_stem_chars"], 17)
        self.assertEqual(s85d["fx3_title_name_max_chars"], 37)
        self.assertEqual(s85d["fx3_slot1_erofs_bypass_events"], 0)
        self.assertEqual(s85d["fx6_title_prefix_max_chars"], 46)

    def test_95_85d_zero_writes_and_zero_leak(self) -> None:
        r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_playback_5items_zero_write_and_reset_immune",
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_96_85d_fx3_title_default_c_accepted(self) -> None:
        r = p372.simulate_85d_playback_viewing_camid_37title_and_erofs(
            operation="fx3_movie_title_37char_settings_boundary",
            title_name=p372.FX3_TITLE_NAME_DEFAULT,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.title_name, "C")
        self.assertEqual(r.title_name_length, 1)

    # =========================================================================
    # Tests 97..104: 4-Mode Determinism, Digest Distinction, CLI, Portability
    #                & Suite 85/85 Milestone Integration
    # =========================================================================

    def test_97_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            force_clean_room=True
        )
        r_f2 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(
            r_f1["phase372_audit_digest_sha256"],
            r_f2["phase372_audit_digest_sha256"],
        )
        self.assertEqual(
            r_f1["phase372_audit_digest_sha256"],
            r_f3["phase372_audit_digest_sha256"],
        )
        self.assertRegex(r_f1["phase372_audit_digest_sha256"], r"^[0-9a-f]{64}$")

        r_dl1 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root=None
        )
        r_dl2 = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            work_root="/nonexistent/phase372_stage85_test"
        )
        self.assertEqual(
            r_dl1["phase372_audit_digest_sha256"],
            r_dl2["phase372_audit_digest_sha256"],
        )

        r_norm = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation()
        if r_norm["source_mode"] == "LOCAL_O_RDONLY_REAL_DONORS":
            self.assertNotEqual(
                r_norm["phase372_audit_digest_sha256"],
                r_f1["phase372_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase372_audit_digest_sha256"],
                r_dl1["phase372_audit_digest_sha256"],
            )

    def test_98_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p372.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_99_standalone_cli_self_test_summary_json_and_help(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p372.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 372 Stage 85 (85/85)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p372.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "85/85")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p372.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("85/85", buf_help.getvalue())

    def test_100_suite_default_config_and_85_of_85_stage_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase372_realhw_metering_pplut_ibis47_camid_pbfile_hil
        )
        self.assertTrue(default_cfg.include_stage85)
        self.assertTrue(
            default_cfg.stage85_realhw_metering_pplut_ibis47_camid_pbfile_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s85 = rep["stage85_realhw_metering_pplut_ibis47_camid_pbfile_hil"]
        self.assertTrue(s85["all_checks_passed"])
        self.assertEqual(s85["phase_number"], 372)
        self.assertEqual(s85["milestone"], "85/85")
        self.assertTrue(s85["is_85th_stage_milestone"])
        self.assertEqual(s85["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s85["slot1_data_sector_writes"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Base 3 stages (stage1, stage2, stage3) + optional phase flags must reach >= 85
        self.assertGreaterEqual(len(stage_keys) + 3, 85)

    def test_101_suite_skip_flags_summary_cli_and_subprocess_clean_room(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_metering_pplut_ibis47_camid_pbfile_hil=",
            buf.getvalue(),
        )
        self.assertIn("m85=85/85", buf.getvalue())

        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc2 = suite.main([*_FAST_CLI_FLAGS, "--skip-stage85", "--json"])
        self.assertEqual(rc2, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertNotIn(
            "stage85_realhw_metering_pplut_ibis47_camid_pbfile_hil",
            rep_skip,
        )

        buf_skip_p = io.StringIO()
        with contextlib.redirect_stdout(buf_skip_p):
            rc3 = suite.main([*_FAST_CLI_FLAGS, "--skip-phase372", "--json"])
        self.assertEqual(rc3, 0)
        rep_skip_p = json.loads(buf_skip_p.getvalue())
        self.assertNotIn(
            "stage85_realhw_metering_pplut_ibis47_camid_pbfile_hil",
            rep_skip_p,
        )

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p372.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Phase 372 Stage 85 (85/85)", proc.stdout)

    def test_102_suite_tamper_detection_fails_on_wrong_milestone(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        with unittest.mock.patch.object(
            p372,
            "run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation",
            wraps=p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation,
        ) as m_run:
            real = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
                force_clean_room=True
            )
            bad = dict(real)
            bad["milestone"] = "84/84"
            m_run.return_value = bad
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])

    def test_103_suite_tamper_detection_fails_on_mxf_hit_or_erofs_bypass(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p372.run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation(
            force_clean_room=True
        )
        for bad_key, bad_val in (
            ("fx3_mxf_hits", 1),
            ("fx3_slot1_erofs_bypass_events", 1),
            ("fx6_has_physical_ibis", True),
        ):
            with unittest.mock.patch.object(
                p372,
                "run_phase372_realhw_metering_pplut_ibis47_camid_pbfile_coemulation",
                return_value={**real, bad_key: bad_val},
            ):
                rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
                self.assertFalse(rep_bad["all_checks_passed"])

    def test_104_run_self_test_wrapper_passes_normal_and_clean_room(self) -> None:
        r_cr = p372.run_self_test(force_clean_room=True)
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertEqual(r_cr["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        r_dl = p372.run_self_test(work_root=None)
        self.assertTrue(r_dl["all_checks_passed"])
        self.assertEqual(r_dl["source_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
