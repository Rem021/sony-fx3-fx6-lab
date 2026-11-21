#!/usr/bin/env python3
"""Unit tests for Phase 376 (Stage 86 — 86/86 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-76 HIL:
- 86A: `[Custom Key/Dial Set.]` 3-Domain Mapping (Still 16 / Movie 16 w/ exact
  `ilc/2210` `TP1000888852` `G100` defaults / Playback 7 skipping `C4`, `Fn`
  strictly Playback-only), `XLR-H1` `0` assignable keys / `0` REC buttons,
  `[Different Set for Still/Mv]` exact 8 items, asymmetric `Common <-> Separate`
  transitions, `[Shutter Mode] = Angle` override, Wave-76 `G99` erratum
  (`Picture Profile` checkbox resists BOTH Reset AND Initialize), `CAMSET` vs
  `CAMPR` & Tier-0 `Slot 1 EROFS=30` vs FX6 `Assignable Button`/`Dial`,
- 86B: `[Gamma Display Assist]` (`Auto`/`S-Log3->709(800%)`/`HLG(BT.2020)`/
  `HLG(709)`, dormant `S-Log2` blocked `EOPNOTSUPP=95`, body LCD only / never
  external HDMI/TV) vs `[Log Shooting]` (`Display LUT` + `Select LUT`, Still
  prompts Gamma Assist `_g 0x6538`, `PPLUT1..4` bake + HDMI `1080p` downscale),
  Reset persistence split vs FX6 zero `Gamma Display Assist`, independent `SDI`
  vs `HDMI` `Output Display`, and 4-way `MLUT` routing,
- 86C: `Wired LAN` USB-LAN (`Auto`/`Manual <=15`, `USB-LAN Cnct. Launch`,
  `VMC-BNCM1`/Wi-Fi mutex), `Access Authen. Settings` (SSH+PTP-IP, zero native
  HTTPS/HTTP Digest, `User`/`Password` charsets, `Generate Password`, SSH Host
  Key Fingerprint, excluded from `CAMSET`), Ver. 7.00+ & `Access Authen.=On`
  disabled `Security(IPsec)`, and Wave-76 `G114`/`G136` Dual-Erratum for
  `[Airplane Mode]` (cuts Wi-Fi/BT RF only, allows USB-LAN Zero-RF bench bypass,
  survives `[Reset Network Set.]`, resets to `Off` ONLY on `[Initialize]`) vs
  FX6 `Wired LAN` mutex & `0` IPsec menus,
- 86D: `[Sensor Cleaning]` (`>=51%` IBIS ultrasonic + mandatory power-off),
  dormant `[Anti-dust Function]`/`[Shutter When Pwr OFF]` blocked `EOPNOTSUPP=95`
  (shutter stays `Open`), `[IR Remote Ctrl]` (`Off` def, resists Reset, suppresses
  `Power Save Start Time`, `BT Rmt` mutex, physically absent on `ILME-FX3A`),
  and Still-only `[Auto Review]` (`Off`/`2`/`5`/`10 Sec`, resists Reset, `0` card
  writes) vs FX6 zero IBIS cleaning (`"The SteadyShot mechanism is fixed."`),
  `2.5mm LANC` + `3.5mm Grip`, and `Rec Review` (108 four-mode tests).
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
import realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulator as p376  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..85 for Stage 86 isolation."""
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
        include_stage85=False,
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
    "--skip-stage85",
]


class TestPhase376Stage86CustomKeyDiffSet8GammaDispMlutUsbLanCleaning(unittest.TestCase):
    # =========================================================================
    # Tests 01..16: Schema, Stage 86 (86/86), Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_phase_and_stage86_constants(self) -> None:
        self.assertEqual(
            p376.SCHEMA_ID,
            "phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation_v1",
        )
        self.assertEqual(p376.PHASE_NUMBER, 376)
        self.assertEqual(p376.STAGE_INDEX, 86)
        self.assertEqual(p376.STAGE_TOTAL, 86)
        self.assertEqual(p376.MILESTONE_LABEL, "86/86")
        self.assertFalse(p376.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertFalse(p376.SLOT1_CAMSET_WRITE_AUTHORIZED)

    def test_02_orchestrator_returns_stage86_and_all_zero_redlines(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["phase_number"], 376)
        self.assertEqual(rep["stage_index"], 86)
        self.assertEqual(rep["stage_total"], 86)
        self.assertEqual(rep["milestone"], "86/86")
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
        self.assertEqual(rep["usb_tx_packets"], 0)
        self.assertEqual(rep["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["passive_tx_bytes_emitted"], 0)
        self.assertFalse(rep["slot1_camset_write_authorized"])
        self.assertEqual(rep["slot1_sector_writes"], 0)
        self.assertEqual(rep["slot1_data_sector_writes"], 0)
        self.assertFalse(rep["slot1_avf_info_mutated"])
        self.assertEqual(rep["rf_tx_packets"], 0)
        self.assertEqual(rep["rf_packets_transmitted"], 0)
        self.assertEqual(rep["rf_nvs_mutation_bytes"], 0)
        self.assertEqual(rep["rsv_orphan_count"], 0)
        self.assertEqual(rep["wf12_00342260_hits"], 0)
        self.assertEqual(rep["appfw_crashes"], 0)
        self.assertEqual(rep["null_gpio_derefs"], 0)
        self.assertEqual(rep["mailbox_stalls"], 0)
        self.assertEqual(rep["stock_cp_fault_count"], 0)
        self.assertEqual(rep["raw_firmware_bytes_leaked"], 0)

    def test_03_donor_spec_counts_18_compact_plus_3_window_equals_21(self) -> None:
        self.assertEqual(len(p376.PHASE376_COMPACT_DONORS), 18)
        self.assertEqual(len(p376.PHASE376_WINDOW_DONORS), 3)
        names = [d.name for d in p376.PHASE376_COMPACT_DONORS] + [
            d.name for d in p376.PHASE376_WINDOW_DONORS
        ]
        self.assertEqual(len(names), 21)
        self.assertEqual(len(set(names)), 21)

    def test_04_donor_inspection_force_clean_room_env(self) -> None:
        info = p376.inspect_phase376_wave76_donors(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(info["total_donors_count"], 21)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_05_donor_inspection_clean_room_test_env(self) -> None:
        info = p376.inspect_phase376_wave76_donors(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["total_donors_count"], 21)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_06_donor_inspection_donorless_work_root_none_and_sentinel(self) -> None:
        d1 = p376.inspect_phase376_wave76_donors(work_root=None)
        d2 = p376.inspect_phase376_wave76_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p376._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(d1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d2["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(d1["total_donors_count"], 21)
        self.assertEqual(d2["total_donors_count"], 21)
        self.assertEqual(d1["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(d2["raw_firmware_bytes_leaked"], 0)

    def test_07_window_donors_bounded_pread_4096_cap(self) -> None:
        info = p376.inspect_phase376_wave76_donors(work_root=None)
        for entry in info["window_donors"]:
            self.assertGreater(entry["windows_verified"], 0)
            self.assertLessEqual(entry["max_pread_bytes"], 4096)

    def test_08_real_local_donors_if_present_verify_strictly_o_rdonly_zero_leak(self) -> None:
        info = p376.inspect_phase376_wave76_donors()
        self.assertIn(
            info["source_mode"],
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if info["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(info["donor_access_mode"], "O_RDONLY_BOUNDED_4K_AND_COMPACT")
        self.assertEqual(info["total_donors_count"], 21)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(info["all_donors_verified"])

    def test_09_compact_donor_tokens_cover_wave76_usblan_airplane_and_fx6_absences(self) -> None:
        by_name = {d.name: d for d in p376.PHASE376_COMPACT_DONORS}
        self.assertIn(b"/usr/kmod/usbnet.ko", by_name["fx3_lib_wired_lan"].required_tokens)
        self.assertIn(b"/usr/sbin/dhcpcd", by_name["fx3_lib_net_service_ether"].required_tokens)
        self.assertIn(b"infra_airplane_mode_init", by_name["fx3_lib_infra_airplane_mode"].required_tokens)
        self.assertIn(b"IPsec", by_name["fx6_string_en"].absent_tokens)
        self.assertIn(b"Different Set for Still/Mv", by_name["fx6_string_en"].absent_tokens)
        self.assertIn(b"The SteadyShot mechanism is fixed.", by_name["fx6_string_en"].required_tokens)

    def test_10_window_donor_tokens_prove_pb_fn_exclusivity_and_fx6_zero_ipsec_menus(self) -> None:
        by_name = {d.name: d for d in p376.PHASE376_WINDOW_DONORS}
        fx3_win = [b for _, _, b in by_name["fx3_appfw"].windows]
        fx3_abs = [b for _, _, b in by_name["fx3_appfw"].absent_windows]
        self.assertIn(b"BKID_APP_setting_custom_key_pb_fn_button", fx3_win)
        self.assertIn(b"MSGID_SSHD_START_CMD", fx3_win)
        self.assertIn(b"BKID_APP_setting_image_sensor_barrier", fx3_win)
        self.assertIn(b"BKID_APP_setting_custom_key_shoot_still_fn_button", fx3_abs)
        self.assertIn(b"BKID_APP_setting_custom_key_movie_fn_button", fx3_abs)

        fx6_abs = [b for _, _, b in by_name["fx6_appfw"].absent_windows]
        self.assertIn(b"BKID_APP_USER_MENU_IPSEC", fx6_abs)
        self.assertIn(b"BKID_APP_USER_MENU_AUTO_REVIEW", fx6_abs)
        self.assertIn(b"BKID_APP_USER_MENU_GAMMA_DISP_ASSIST", fx6_abs)

    def test_11_stage86_probe_submodels_all_true(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        probe = rep["stage86_probe"]
        self.assertEqual(probe["stage_index"], 86)
        self.assertEqual(probe["stage_total"], 86)
        self.assertEqual(probe["milestone_label"], "86/86")
        self.assertTrue(probe["submodel_86a_passed"])
        self.assertTrue(probe["submodel_86b_passed"])
        self.assertTrue(probe["submodel_86c_passed"])
        self.assertTrue(probe["submodel_86d_passed"])
        self.assertFalse(probe["ready_for_live_camera_attach"])

    def test_12_strip_wall_clock_recursively_strips_elapsed_seconds_and_ms(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.123,
            "elapsed_ms": 123,
            "nested": [{"elapsed_seconds": 9.9, "elapsed_ms": 9900, "keep": "ok"}],
        }
        stripped = p376._strip_wall_clock(sample)
        self.assertEqual(stripped, {"a": 1, "nested": [{"keep": "ok"}]})

    def test_13_audit_digest_64_hex_chars_and_deterministic(self) -> None:
        r1 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        r2 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        self.assertRegex(r1["phase376_audit_digest_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            r1["phase376_audit_digest_sha256"],
            r2["phase376_audit_digest_sha256"],
        )

    def test_14_explicit_posix_errno_constants(self) -> None:
        self.assertEqual(p376.EPERM_ERRNO, 1)
        self.assertEqual(p376.EAGAIN_ERRNO, 11)
        self.assertEqual(p376.EBUSY_ERRNO, 16)
        self.assertEqual(p376.ENODEV_ERRNO, 19)
        self.assertEqual(p376.EINVAL_ERRNO, 22)
        self.assertEqual(p376.EROFS_ERRNO, 30)
        self.assertEqual(p376.EOPNOTSUPP_ERRNO, 95)

    def test_15_nonexistent_work_root_falls_back_cleanly_zero_leak(self) -> None:
        info = p376.inspect_phase376_wave76_donors(work_root="/nonexistent_stage86_dir")
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(info["all_donors_verified"])

    def test_16_bounded_read_helper_rejects_oversize_request(self) -> None:
        with self.assertRaises(p376.Stage86Phase376Error):
            p376._read_bounded_window_o_rdonly(Path("/dev/null"), 0, size=8192)

    # =========================================================================
    # Tests 17..40: Sub-Model 86A — Custom Key/Dial Set. 3-Domain & Diff Set 8-Bit
    # =========================================================================

    def test_17_86a_still_domain_exact_16_controls_and_movie_button_exception(self) -> None:
        self.assertEqual(len(p376.FX3_STILL_CUSTOM_DEFAULTS), 16)
        for ctrl, exp in p376.FX3_STILL_CUSTOM_DEFAULTS.items():
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping",
                domain="Still",
                control_name=ctrl,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.default_assignment, exp)
            if ctrl == "MOVIE Button":
                self.assertEqual(r.default_assignment, "Movie Shooting")
            else:
                self.assertEqual(r.default_assignment, "Follow Custom")

    def test_18_86a_movie_domain_exact_16_controls_tp1000888852_g100_defaults(self) -> None:
        self.assertEqual(len(p376.FX3_MOVIE_CUSTOM_DEFAULTS), 16)
        expected_core = {
            "Front dial": "Aperture",
            "Rear dial": "ISO / Exposure Index",
            "Control Wheel": "Shutter Speed",
            "Custom Button 1": "L.PressAv Auto/Manual",
            "Custom Button 2": "White Balance",
            "Custom Button 3": "L.PressISO Auto/Manual",
            "Custom Button 4": "Not set",
            "Custom Button 5": "Focus Magnifier",
            "Custom Button 6": "Movie Shooting",
            "Multi-Slc Center Btn": "Focus Standard",
            "Center Button": "Not set",
            "Left Button": "Zebra Display Select",
            "Right Button": "Peaking Display Select",
            "Down Button": "L.PressTv Auto/Manual",
            "MOVIE Button": "Movie Shooting",
            "Focus Hold Button": "Focus Hold",
        }
        for ctrl, exp in expected_core.items():
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping",
                domain="Movie",
                control_name=ctrl,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.default_assignment, exp)
            self.assertTrue(r.g100_default_keymap_reconciled)

    def test_19_86a_playback_domain_exact_7_controls_with_fn_and_no_c4(self) -> None:
        self.assertEqual(len(p376.FX3_PLAYBACK_CUSTOM_DEFAULTS), 7)
        for ctrl, exp in p376.FX3_PLAYBACK_CUSTOM_DEFAULTS.items():
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping",
                domain="Playback",
                control_name=ctrl,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.default_assignment, exp)
        r_c4 = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_custom_key_3domain_mapping",
            domain="Playback",
            control_name="Custom Button 4",
        )
        self.assertFalse(r_c4.allowed)
        self.assertEqual(r_c4.errno, p376.EOPNOTSUPP_ERRNO)

    def test_20_86a_fn_button_strictly_playback_only_blocked_in_still_and_movie(self) -> None:
        for dom in ("Still", "Movie"):
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping",
                domain=dom,
                control_name="Fn Button",
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)

    def test_21_86a_xlr_h1_handle_zero_assignable_keys_and_zero_rec_buttons(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_custom_key_3domain_mapping",
            xlr_h1_key_requested=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.ENODEV_ERRNO)
        self.assertEqual(r.xlr_h1_assignable_keys, 0)
        self.assertEqual(r.xlr_h1_rec_buttons, 0)

    def test_22_86a_dormant_alpha_controls_blocked_eopnotsupp(self) -> None:
        for ctrl in p376.FX3_DORMANT_ALPHA_CONTROLS:
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping",
                domain="Movie",
                control_name=ctrl,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)

    def test_23_86a_unknown_control_name_returns_einval(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_custom_key_3domain_mapping",
            domain="Movie",
            control_name="Phantom Button 99",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_24_86a_dial_separation_mode_checkboxes_supported(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_custom_key_3domain_mapping",
            domain="Movie",
            control_name="Front dial",
            separate_m_and_other_modes=True,
            separate_flex_exp_and_iauto=True,
        )
        self.assertTrue(r.allowed)
        self.assertIn("SEP_M_OTHER", r.reason)
        self.assertIn("SEP_FLEX_IAUTO", r.reason)

    def test_25_86a_diff_set_exact_8_items_verified(self) -> None:
        self.assertEqual(
            p376.FX3_DIFF_SET_8_ITEMS,
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
        self.assertEqual(len(p376.FX3_DIFF_SET_8_ITEMS), 8)

    def test_26_86a_diff_set_common_to_separate_standard_copies_both_still_and_movie(self) -> None:
        for item in p376.FX3_DIFF_SET_8_ITEMS:
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_diff_set_8bit_transitions",
                diff_set_item=item,
                transition="Common->Separate",
                is_custom_wb=False,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.still_inherited_value)
            self.assertTrue(r.movie_inherited_value)

    def test_27_86a_diff_set_common_to_separate_custom_wb_still_only_exception(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_diff_set_8bit_transitions",
            diff_set_item="White Balance",
            transition="Common->Separate",
            is_custom_wb=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.still_inherited_value)
        self.assertFalse(r.movie_inherited_value)

    def test_28_86a_diff_set_separate_to_common_factory_reset_for_standard_items(self) -> None:
        for item in ("ISO", "Exposure Comp.", "Metering Mode", "White Balance", "Picture Profile", "Focus Mode"):
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_diff_set_8bit_transitions",
                diff_set_item=item,
                transition="Separate->Common",
                is_custom_wb=False,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.reverted_to_factory_default)
            self.assertFalse(r.common_inherited_still_value)

    def test_29_86a_diff_set_separate_to_common_aperture_shutter_customwb_inherit_still(self) -> None:
        for item, cwb in (("Aperture", False), ("Shutter Speed", False), ("White Balance", True)):
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_diff_set_8bit_transitions",
                diff_set_item=item,
                transition="Separate->Common",
                is_custom_wb=cwb,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.common_inherited_still_value)
            self.assertFalse(r.reverted_to_factory_default)

    def test_30_86a_shutter_mode_angle_penetration_override_remains_independent(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_diff_set_8bit_transitions",
            diff_set_item="Shutter Speed",
            transition="Separate->Common",
            shutter_mode="Angle",
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.shutter_angle_independent_override)

    def test_31_86a_diff_set_invalid_item_transition_or_shutter_mode_einval(self) -> None:
        for kw in (
            {"diff_set_item": "Creative Look"},
            {"transition": "Sideways"},
            {"shutter_mode": "ECS"},
        ):
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_diff_set_8bit_transitions",
                **kw,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_32_86a_camera_settings_reset_preserves_custom_key_and_all_8_diff_set(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_customkey_diffset_reset_init_and_camset_erofs",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.custom_key_preserved)
        self.assertTrue(r.diff_set_other7_preserved)
        self.assertTrue(r.diff_set_pp_checkbox_preserved)
        self.assertTrue(r.camset_included)
        self.assertFalse(r.campr_included)

    def test_33_86a_g99_erratum_initialize_resets_customkey_and_7_items_but_preserves_pp_checkbox(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_customkey_diffset_reset_init_and_camset_erofs",
            initialize_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.custom_key_preserved)
        self.assertFalse(r.diff_set_other7_preserved)
        self.assertTrue(r.diff_set_pp_checkbox_preserved)
        self.assertTrue(r.g99_pp_init_erratum_reconciled)

    def test_34_86a_slot1_camset_write_hard_blocked_erofs30_zero_writes(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_customkey_diffset_reset_init_and_camset_erofs",
            camset_slot1_write_requested=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EROFS_ERRNO)
        self.assertFalse(r.slot1_camset_write_authorized)
        self.assertEqual(r.slot1_sector_writes, 0)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_35_86a_fx6_assignable_buttons_1_to_9_and_dials_with_direction(self) -> None:
        for btn in p376.FX6_ASSIGNABLE_BUTTONS:
            for dial in p376.FX6_ASSIGNABLE_DIALS:
                for direc in p376.FX6_DIAL_DIRECTIONS:
                    r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                        operation="fx6_assignable_buttons_dials_no_still_mv_split",
                        body_model=p376.BODY_MODEL_FX6,
                        fx6_assignable_button=btn,
                        fx6_assignable_dial=dial,
                        fx6_dial_direction=direc,
                    )
                    self.assertTrue(r.allowed)
                    self.assertEqual(r.fx6_assignable_button, btn)
                    self.assertEqual(r.fx6_assignable_dial, dial)
                    self.assertEqual(r.fx6_dial_direction, direc)

    def test_36_86a_fx6_rejects_diff_set_still_mv_split_eopnotsupp(self) -> None:
        r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx6_assignable_buttons_dials_no_still_mv_split",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_diff_set_still_mv=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)

    def test_37_86a_fx6_invalid_button_dial_direction_einval(self) -> None:
        for kw in (
            {"fx6_assignable_button": "<12>"},
            {"fx6_assignable_dial": "Front Wheel"},
            {"fx6_dial_direction": "Invert"},
        ):
            r = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx6_assignable_buttons_dials_no_still_mv_split",
                body_model=p376.BODY_MODEL_FX6,
                **kw,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_38_86a_cross_body_rejections_eopnotsupp(self) -> None:
        r1 = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx3_custom_key_3domain_mapping",
            body_model=p376.BODY_MODEL_FX6,
        )
        r2 = p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
            operation="fx6_assignable_buttons_dials_no_still_mv_split",
            body_model=p376.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p376.EOPNOTSUPP_ERRNO)

    def test_39_86a_invalid_dispatch_raises_stage86_error(self) -> None:
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(operation="bad_86a")
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping", body_model="FX9"
            )
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
                operation="fx3_custom_key_3domain_mapping", domain="S&Q"
            )

    def test_40_86a_orchestrator_metrics_and_zero_writes(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        s86a = rep["submodel_86a_customkey_3domain_diffset8_fx6_assign"]
        self.assertTrue(s86a["passed"])
        self.assertEqual(s86a["fx3_still_controls_count"], 16)
        self.assertEqual(s86a["fx3_movie_controls_count"], 16)
        self.assertEqual(s86a["fx3_playback_controls_count"], 7)
        self.assertEqual(s86a["fx3_xlr_h1_assignable_keys"], 0)
        self.assertEqual(s86a["fx3_xlr_h1_rec_buttons"], 0)
        self.assertEqual(s86a["fx3_diff_set_items_count"], 8)
        self.assertTrue(s86a["fx3_g99_pp_init_erratum_reconciled"])
        self.assertFalse(s86a["slot1_camset_write_authorized"])

    # =========================================================================
    # Tests 41..62: Sub-Model 86B — Gamma Display Assist vs Display LUT / FX6 MLUT
    # =========================================================================

    def test_41_86b_all_4_gamma_assist_types_accepted_lcd_only_never_hdmi(self) -> None:
        self.assertEqual(len(p376.FX3_GAMMA_DISP_ASSIST_TYPES), 4)
        for gtype in p376.FX3_GAMMA_DISP_ASSIST_TYPES:
            r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_gamma_assist_and_dormant_slog2",
                gamma_display_assist="On",
                gamma_disp_assist_type=gtype,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.body_lcd_gamma_assist_applied)
            self.assertFalse(r.external_hdmi_tv_gamma_assist_applied)

    def test_42_86b_dormant_slog2_strictly_blocked_eopnotsupp95(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            gamma_display_assist="On",
            gamma_disp_assist_type="S-Log2",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dormant_slog2_blocked)

    def test_43_86b_auto_gamma_assist_resolution_slog3_hlg2020_hlg709_hlgstill(self) -> None:
        cases = [
            (dict(pp_gamma="S-Log3", pp_color_mode="S-Gamut3.Cine", hlg_still_image=False), "S-Log3->709(800%)"),
            (dict(pp_gamma="HLG3", pp_color_mode="BT.2020", hlg_still_image=False), "HLG(BT.2020)"),
            (dict(pp_gamma="HLG2", pp_color_mode="709", hlg_still_image=False), "HLG(709)"),
            (dict(pp_gamma="ITU709", pp_color_mode="709", hlg_still_image=True), "HLG(BT.2020)"),
        ]
        for kw, expected in cases:
            r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_gamma_assist_and_dormant_slog2",
                gamma_display_assist="On",
                gamma_disp_assist_type="Auto",
                **kw,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.resolved_auto_assist_curve, expected)
            self.assertFalse(r.external_hdmi_tv_gamma_assist_applied)

    def test_44_86b_gamma_assist_off_applies_neither_lcd_nor_hdmi(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            gamma_display_assist="Off",
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.body_lcd_gamma_assist_applied)
        self.assertFalse(r.external_hdmi_tv_gamma_assist_applied)

    def test_45_86b_log_shooting_movie_hard_locks_gamma_assist_off_all_3_modes(self) -> None:
        for lmode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_log_shooting_priority_vs_still_and_pplut",
                shoot_mode="Movie",
                log_shooting_mode=lmode,
                gamma_display_assist="On",
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.gamma_assist_hard_locked_off)
            self.assertEqual(r.gamma_display_assist, "Off")

    def test_46_86b_log_shooting_movie_hands_over_to_display_lut_and_select_lut(self) -> None:
        self.assertEqual(len(p376.FX3_SELECT_LUT_ALL_OPTIONS), 19)
        for lut in ("S-Log3", "s709", "709(800%)", "User1", "User16"):
            r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_log_shooting_priority_vs_still_and_pplut",
                shoot_mode="Movie",
                log_shooting_mode="Cine EI",
                gamma_display_assist="Off",
                display_lut="On",
                select_lut=lut,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.gamma_assist_hard_locked_off)
            self.assertEqual(r.display_lut, "On")
            self.assertEqual(r.select_lut, lut)

    def test_47_86b_log_shooting_still_prompts_gamma_display_assist_instead_of_lut(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            shoot_mode="Still",
            log_shooting_mode="Cine EI",
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.still_log_prompts_gamma_assist)
        self.assertEqual(r.gamma_display_assist, "On")
        self.assertEqual(r.display_lut, "Off")
        self.assertFalse(r.external_hdmi_tv_gamma_assist_applied)

    def test_48_86b_pplut1_to_4_bakes_pixels_and_forces_hdmi_1080p_downscale_during_rec(self) -> None:
        for slot in p376.FX3_PPLUT_SLOTS:
            r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_log_shooting_priority_vs_still_and_pplut",
                shoot_mode="Movie",
                log_shooting_mode="Off",
                pplut_slot=slot,
                internal_rec_active=True,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.lut_baked_into_rec_pixels)
            self.assertTrue(r.hdmi_forced_1080p_downscale)

    def test_49_86b_pplut_hdmi_only_or_raw_on_avoids_1080p_downscale(self) -> None:
        r_ho = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            shoot_mode="Movie",
            log_shooting_mode="Off",
            pplut_slot="PPLUT2",
            hdmi_only_no_internal_rec=True,
        )
        r_raw = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            shoot_mode="Movie",
            log_shooting_mode="Off",
            pplut_slot="PPLUT2",
            hdmi_raw_on=True,
        )
        self.assertTrue(r_ho.allowed)
        self.assertFalse(r_ho.hdmi_forced_1080p_downscale)
        self.assertTrue(r_raw.allowed)
        self.assertFalse(r_raw.hdmi_forced_1080p_downscale)

    def test_50_86b_pplut_blocked_in_still_mode_eopnotsupp(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            shoot_mode="Still",
            log_shooting_mode="Off",
            pplut_slot="PPLUT1",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)

    def test_51_86b_camera_settings_reset_preserves_setup_items_resets_select_lut_s709(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_displaylut_reset_persistence",
            gamma_display_assist="On",
            gamma_disp_assist_type="HLG(709)",
            display_lut="Off",
            select_lut="User8",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.setup_display_items_preserved)
        self.assertTrue(r.select_lut_reset_to_s709)
        self.assertEqual(r.gamma_display_assist, "On")
        self.assertEqual(r.gamma_disp_assist_type, "HLG(709)")
        self.assertEqual(r.display_lut, "Off")
        self.assertEqual(r.select_lut, "s709")

    def test_52_86b_initialize_resets_all_4_gamma_and_lut_settings(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_displaylut_reset_persistence",
            gamma_display_assist="On",
            gamma_disp_assist_type="HLG(BT.2020)",
            display_lut="Off",
            select_lut="User12",
            initialize_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertFalse(r.setup_display_items_preserved)
        self.assertEqual(r.gamma_display_assist, "Off")
        self.assertEqual(r.gamma_disp_assist_type, "Auto")
        self.assertEqual(r.display_lut, "On")
        self.assertEqual(r.select_lut, "s709")

    def test_53_86b_fx6_zero_user_exposed_gamma_display_assist_eopnotsupp(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_gamma_assist=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.fx6_gamma_assist_user_menus, 0)

    def test_54_86b_fx6_independent_sdi_vs_hdmi_output_display_and_4way_mlut(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
            body_model=p376.BODY_MODEL_FX6,
            fx6_sdi_osd_on=True,
            fx6_hdmi_osd_on=False,
            fx6_mlut_routing={
                "Internal Rec": True,
                "SDI1/2+HDMI": False,
                "LCD/VF": True,
                "Proxy/VF Streaming": False,
            },
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.fx6_sdi_osd_on)
        self.assertFalse(r.fx6_hdmi_osd_on)
        self.assertEqual(len(r.fx6_mlut_routing), 4)
        self.assertTrue(r.fx6_mlut_routing["Internal Rec"])
        self.assertFalse(r.fx6_mlut_routing["SDI1/2+HDMI"])
        self.assertTrue(r.fx6_mlut_routing["LCD/VF"])
        self.assertFalse(r.fx6_mlut_routing["Proxy/VF Streaming"])

    def test_55_86b_fx6_invalid_mlut_route_key_einval(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
            body_model=p376.BODY_MODEL_FX6,
            fx6_mlut_routing={"USB-UVC": True},
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_56_86b_invalid_gamma_type_state_and_select_lut_einval(self) -> None:
        r1 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            gamma_disp_assist_type="Rec2100-PQ",
        )
        r2 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            gamma_display_assist="Auto",
        )
        r3 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            select_lut="User17",
        )
        self.assertEqual(r1.errno, p376.EINVAL_ERRNO)
        self.assertEqual(r2.errno, p376.EINVAL_ERRNO)
        self.assertEqual(r3.errno, p376.EINVAL_ERRNO)

    def test_57_86b_invalid_pplut_and_display_lut_einval(self) -> None:
        r1 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            pplut_slot="PPLUT5",
        )
        r2 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_log_shooting_priority_vs_still_and_pplut",
            display_lut="Auto",
        )
        self.assertEqual(r1.errno, p376.EINVAL_ERRNO)
        self.assertEqual(r2.errno, p376.EINVAL_ERRNO)

    def test_58_86b_gamma_assist_in_log_mode_blocked_in_sq_too(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            shoot_mode="S&Q",
            log_shooting_mode="Flexible ISO",
            gamma_display_assist="On",
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.gamma_assist_hard_locked_off)

    def test_59_86b_cross_body_rejections_eopnotsupp(self) -> None:
        r1 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2",
            body_model=p376.BODY_MODEL_FX6,
        )
        r2 = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
            body_model=p376.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p376.EOPNOTSUPP_ERRNO)

    def test_60_86b_invalid_dispatch_raises_stage86_error(self) -> None:
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(operation="bad_86b")
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_gamma_assist_and_dormant_slog2", body_model="FX30"
            )
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
                operation="fx3_gamma_assist_and_dormant_slog2", shoot_mode="Playback"
            )

    def test_61_86b_orchestrator_metrics_alignment(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        s86b = rep["submodel_86b_gammadisp_displaylut_fx6_mlut"]
        self.assertTrue(s86b["passed"])
        self.assertEqual(s86b["fx3_gamma_assist_types_count"], 4)
        self.assertEqual(s86b["fx3_dormant_slog2_exposed_events"], 0)
        self.assertEqual(s86b["fx3_hdmi_gamma_assist_applied_events"], 0)
        self.assertEqual(s86b["fx3_select_lut_options_count"], 19)
        self.assertEqual(s86b["fx6_gamma_assist_user_menus"], 0)
        self.assertEqual(s86b["fx6_mlut_routes_count"], 4)

    def test_62_86b_zero_writes_and_zero_leak(self) -> None:
        r = p376.simulate_86b_gammadisp_displaylut_and_fx6_mlut(
            operation="fx3_gamma_assist_and_dormant_slog2"
        )
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    # =========================================================================
    # Tests 63..84: Sub-Model 86C — USB-LAN, Access Authen, IPsec & Airplane Mode
    # =========================================================================

    def test_63_86c_wired_lan_auto_and_manual_valid_ipv4_excluded_from_camset(self) -> None:
        r_auto = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            ip_setting_mode="Auto",
            usb_lan_cnct_launch=False,
        )
        r_man = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            ip_setting_mode="Manual",
            manual_ip="192.168.100.254",
            manual_subnet="255.255.255.0",
            manual_gateway="192.168.100.1",
            manual_dns1="1.1.1.1",
            manual_dns2="9.9.9.9",
            usb_lan_cnct_launch=True,
        )
        self.assertTrue(r_auto.allowed)
        self.assertTrue(r_man.allowed)
        self.assertFalse(r_man.camset_included)
        self.assertEqual(r_man.rf_tx_packets, 0)
        self.assertEqual(r_man.usb_tx_packets, 0)

    def test_64_86c_wired_lan_invalid_manual_ipv4_fields_einval(self) -> None:
        for bad_kw in (
            {"manual_ip": "192.168.100.256"},
            {"manual_ip": "192.168.100.2540"},  # 16 chars > 15
            {"manual_subnet": "255.255.255.abc"},
            {"manual_gateway": "192.168.1"},
            {"manual_dns1": "01.2.3.4"},
            {"manual_dns2": ""},
        ):
            r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx3_wired_lan_usblan_and_mutex",
                ip_setting_mode="Manual",
                **bad_kw,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_65_86c_wired_lan_mutex_with_multi_micro_usb_vmcbncm1_and_wifi_ebusy(self) -> None:
        r_vmc = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            multi_micro_usb_data_active=True,
        )
        r_wifi = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            wifi_active=True,
        )
        self.assertFalse(r_vmc.allowed)
        self.assertEqual(r_vmc.errno, p376.EBUSY_ERRNO)
        self.assertFalse(r_wifi.allowed)
        self.assertEqual(r_wifi.errno, p376.EBUSY_ERRNO)

    def test_66_86c_access_authen_ssh_ptpip_default_on_zero_https_and_fingerprint(self) -> None:
        self.assertTrue(p376.FX3_ACCESS_AUTHEN_DEFAULT)
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_access_authen_ssh_ptpip",
            access_authen_on=True,
            username="User!%.=_99",
            password="Pass!%.=_+,-123",
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.transport_protocol, "SSH+PTP-IP")
        self.assertFalse(r.native_https_server_present)
        self.assertFalse(r.http_digest_server_present)
        self.assertTrue(r.ssh_host_key_fingerprint.startswith("SHA256:"))
        self.assertFalse(r.camset_included)

    def test_67_86c_access_authen_rejects_native_https_or_http_digest_eopnotsupp(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_access_authen_ssh_ptpip",
            request_native_https_or_digest=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.native_https_server_present)
        self.assertFalse(r.http_digest_server_present)

    def test_68_86c_access_authen_user_and_password_charset_and_length_bounds(self) -> None:
        for bad_u in ("", "A" * 17, "bad-user", "bad+user", "bad user", "user@host"):
            r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx3_access_authen_ssh_ptpip",
                username=bad_u,
            )
            self.assertFalse(r.allowed, f"Username {bad_u!r} should fail")
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

        for bad_p in ("short7!", "A" * 17, "bad pass 123", "bad@pass123"):
            r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx3_access_authen_ssh_ptpip",
                password=bad_p,
            )
            self.assertFalse(r.allowed, f"Password {bad_p!r} should fail")
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_69_86c_access_authen_generate_password_deterministic_and_valid(self) -> None:
        r1 = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_access_authen_ssh_ptpip",
            username="bench_user",
            generate_password_requested=True,
        )
        r2 = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_access_authen_ssh_ptpip",
            username="bench_user",
            generate_password_requested=True,
        )
        self.assertTrue(r1.allowed)
        self.assertEqual(r1.generated_password, r2.generated_password)
        self.assertRegex(r1.generated_password, p376.FX3_ACCESS_AUTHEN_PASS_RE)

    def test_70_86c_access_authen_off_falls_back_to_plaintext_warning(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_access_authen_ssh_ptpip",
            access_authen_on=False,
        )
        self.assertTrue(r.allowed)
        self.assertEqual(r.transport_protocol, "PLAINTEXT_PTP-IP")

    def test_71_86c_security_ipsec_hard_disabled_on_fw_v700_and_v702(self) -> None:
        for fw in ("7.00", "7.02", "8.00"):
            for auth in (True, False):
                r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                    operation="fx3_security_ipsec_v700_and_authen_lock",
                    firmware_version=fw,
                    access_authen_on=auth,
                )
                self.assertFalse(r.allowed)
                self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
                self.assertFalse(r.ipsec_available)
                self.assertTrue(r.ipsec_disabled_by_fw_v700)

    def test_72_86c_security_ipsec_hard_disabled_on_legacy_fw_when_access_authen_on(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_security_ipsec_v700_and_authen_lock",
            firmware_version="6.00",
            access_authen_on=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.ipsec_disabled_by_fw_v700)
        self.assertTrue(r.ipsec_disabled_by_access_authen)

    def test_73_86c_security_ipsec_legacy_pre700_authen_off_validates_ikev2_24h(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_security_ipsec_v700_and_authen_lock",
            firmware_version="6.00",
            access_authen_on=False,
            ipsec_dest_ip="192.168.10.100",
            ipsec_shared_key="1234567890abcdef",
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.ipsec_available)
        self.assertEqual(r.ipsec_rekey_hours, 24)
        self.assertIn("AES-128-CBC", r.ipsec_cipher_suite)
        self.assertIn("DH-3072", r.ipsec_cipher_suite)
        self.assertIn("HMAC-SHA-384-192", r.ipsec_cipher_suite)

    def test_74_86c_security_ipsec_legacy_invalid_dest_ip_or_key_einval(self) -> None:
        for kw in (
            {"firmware_version": "v7"},
            {"ipsec_dest_ip": "1" * 47},
            {"ipsec_shared_key": "short7"},
            {"ipsec_shared_key": "K" * 21},
        ):
            r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx3_security_ipsec_v700_and_authen_lock",
                firmware_version=kw.get("firmware_version", "6.00"),
                access_authen_on=False,
                ipsec_dest_ip=kw.get("ipsec_dest_ip", "10.0.0.1"),
                ipsec_shared_key=kw.get("ipsec_shared_key", "1234567890abcdef"),
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_75_86c_airplane_mode_cuts_wifi_bt_rf_allows_wired_usblan_zero_rf_bypass(self) -> None:
        r_lan = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
            usblan_requested_in_airplane=True,
        )
        self.assertTrue(r_lan.allowed)
        self.assertTrue(r_lan.wifi_rf_blocked)
        self.assertTrue(r_lan.bt_rf_blocked)
        self.assertTrue(r_lan.usblan_allowed_in_airplane_mode)
        self.assertTrue(r_lan.zero_rf_wired_bench_bypass)
        self.assertEqual(r_lan.rf_tx_packets, 0)

        r_rf = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
            wifi_or_bt_requested_in_airplane=True,
        )
        self.assertFalse(r_rf.allowed)
        self.assertEqual(r_rf.errno, p376.EPERM_ERRNO)
        self.assertEqual(r_rf.rf_tx_packets, 0)

    def test_76_86c_wave76_g114_g136_dual_erratum_airplane_survives_reset_network_set(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
            ip_setting_mode="Manual",
            usb_lan_cnct_launch=True,
            access_authen_on=False,
            reset_network_set_triggered=True,
        )
        self.assertTrue(r.allowed)
        self.assertTrue(r.airplane_mode_on)
        self.assertTrue(r.airplane_mode_survived_net_reset)
        self.assertFalse(r.airplane_mode_reset_on_initialize)
        self.assertTrue(r.g114_g136_dual_erratum_reconciled)
        # Other network items DO reset on [Reset Network Set.]
        self.assertEqual(r.ip_setting_mode, "Auto")
        self.assertFalse(r.usb_lan_cnct_launch)
        self.assertTrue(r.access_authen_on)

    def test_77_86c_wave76_g114_g136_dual_erratum_airplane_resets_to_off_only_on_initialize(self) -> None:
        r_cam = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_cam.allowed)
        self.assertTrue(r_cam.airplane_mode_on)

        r_init = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertFalse(r_init.airplane_mode_on)
        self.assertTrue(r_init.airplane_mode_reset_on_initialize)

    def test_78_86c_fx6_wired_lan_authen_ok_and_zero_ipsec_user_menus(self) -> None:
        r_ok = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
            body_model=p376.BODY_MODEL_FX6,
        )
        self.assertTrue(r_ok.allowed)
        self.assertEqual(r_ok.fx6_ipsec_user_menus, 0)

        r_ipsec = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_ipsec=True,
        )
        self.assertFalse(r_ipsec.allowed)
        self.assertEqual(r_ipsec.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_ipsec.fx6_ipsec_user_menus, 0)

    def test_79_86c_fx6_wired_lan_mutex_with_wireless_modem_simul_rec(self) -> None:
        for mode in p376.FX6_WIRED_LAN_MUTEX_MODES:
            r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
                body_model=p376.BODY_MODEL_FX6,
                fx6_mutex_mode=mode,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EBUSY_ERRNO)

        r_bad = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
            body_model=p376.BODY_MODEL_FX6,
            fx6_mutex_mode="Bluetooth",
        )
        self.assertEqual(r_bad.errno, p376.EINVAL_ERRNO)

    def test_80_86c_invalid_ip_setting_mode_einval(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            ip_setting_mode="StaticV6",
        )
        self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_81_86c_cross_body_rejections_eopnotsupp(self) -> None:
        r1 = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_wired_lan_usblan_and_mutex",
            body_model=p376.BODY_MODEL_FX6,
        )
        r2 = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
            body_model=p376.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p376.EOPNOTSUPP_ERRNO)

    def test_82_86c_invalid_dispatch_raises_stage86_error(self) -> None:
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(operation="bad_86c")
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
                operation="fx3_wired_lan_usblan_and_mutex", body_model="FX9"
            )

    def test_83_86c_orchestrator_metrics_alignment(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        s86c = rep["submodel_86c_usblan_auth_ipsec_airplane_fx6_net"]
        self.assertTrue(s86c["passed"])
        self.assertEqual(s86c["fx3_ipsec_v700_bypass_events"], 0)
        self.assertTrue(s86c["fx3_airplane_g114_g136_erratum_reconciled"])
        self.assertFalse(s86c["fx3_native_https_server_present"])
        self.assertEqual(s86c["fx6_ipsec_user_menus"], 0)
        self.assertEqual(s86c["rf_tx_packets"], 0)
        self.assertEqual(s86c["usb_tx_packets"], 0)

    def test_84_86c_zero_rf_zero_usb_zero_writes(self) -> None:
        r = p376.simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
            operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
            airplane_mode_on=True,
        )
        self.assertEqual(r.rf_tx_packets, 0)
        self.assertEqual(r.rf_packets_transmitted, 0)
        self.assertEqual(r.usb_tx_packets, 0)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)

    # =========================================================================
    # Tests 85..100: Sub-Model 86D — Sensor Cleaning (>=51% IBIS), IR & Auto Review
    # =========================================================================

    def test_85_86d_sensor_cleaning_51_to_100pct_triggers_ibis_and_poweroff_prompt(self) -> None:
        for pct in (51, 75, 100):
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
                battery_pct=pct,
            )
            self.assertTrue(r.allowed)
            self.assertTrue(r.ibis_ultrasonic_triggered)
            self.assertFalse(r.low_battery_blocked)
            self.assertTrue(r.mandatory_power_off_prompt_shown)
            self.assertEqual(r.shutter_curtain_at_power_off, "Open")

    def test_86_86d_sensor_cleaning_below_51pct_blocked_eagain(self) -> None:
        for pct in (0, 25, 50):
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
                battery_pct=pct,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EAGAIN_ERRNO)
            self.assertFalse(r.ibis_ultrasonic_triggered)
            self.assertTrue(r.low_battery_blocked)

    def test_87_86d_sensor_cleaning_proceed_without_poweroff_blocked_eperm(self) -> None:
        r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
            battery_pct=80,
            proceed_blower_without_power_off=True,
        )
        self.assertFalse(r.allowed)
        self.assertEqual(r.errno, p376.EPERM_ERRNO)
        self.assertTrue(r.mandatory_power_off_enforced)

    def test_88_86d_sensor_cleaning_invalid_battery_pct_einval(self) -> None:
        for bad in (-1, 101, True, False):
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
                battery_pct=bad,  # type: ignore[arg-type]
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_89_86d_dormant_antidust_and_shutter_when_pwr_off_blocked_eopnotsupp95(self) -> None:
        for menu in p376.FX3_DORMANT_ANTIDUST_MENUS:
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_dormant_antidust_and_shutter_pwr_off_blocked",
                dormant_menu_requested=menu,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p376.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_antidust_or_shutter_blocked)
            self.assertEqual(r.shutter_curtain_at_power_off, "Open")

        r_bad = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_dormant_antidust_and_shutter_pwr_off_blocked",
            dormant_menu_requested="Unknown Menu",
        )
        self.assertEqual(r_bad.errno, p376.EINVAL_ERRNO)

    def test_90_86d_ir_remote_ctrl_suppresses_power_save_and_resists_cam_reset(self) -> None:
        r_on = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
            ir_remote_ctrl_on=True,
        )
        self.assertTrue(r_on.allowed)
        self.assertTrue(r_on.ir_remote_ctrl_on)
        self.assertTrue(r_on.power_save_start_time_suppressed)

        r_rst = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
            ir_remote_ctrl_on=True,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertTrue(r_rst.ir_remote_ctrl_on)
        self.assertTrue(r_rst.setup_item_survived_cam_reset)

        r_init = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
            ir_remote_ctrl_on=True,
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertFalse(r_init.ir_remote_ctrl_on)
        self.assertTrue(r_init.setup_item_reset_on_initialize)

    def test_91_86d_ir_remote_ctrl_mutex_with_bt_rmt_and_absent_on_fx3a(self) -> None:
        r_bt = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
            ir_remote_ctrl_on=True,
            bt_rmt_ctrl_on=True,
        )
        self.assertFalse(r_bt.allowed)
        self.assertEqual(r_bt.errno, p376.EBUSY_ERRNO)
        self.assertTrue(r_bt.ir_blocked_by_bt_rmt)

        r_fx3a = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
            body_variant=p376.BODY_MODEL_FX3A,
            ir_remote_ctrl_on=True,
        )
        self.assertFalse(r_fx3a.allowed)
        self.assertEqual(r_fx3a.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_fx3a.fx3a_ir_physically_absent)

    def test_92_86d_auto_review_all_4_options_still_only_and_zero_card_writes(self) -> None:
        self.assertEqual(p376.FX3_AUTO_REVIEW_DEFAULT, "Off")
        for opt in p376.FX3_AUTO_REVIEW_OPTIONS:
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_auto_review_still_only_and_reset",
                shoot_mode="Still",
                auto_review_setting=opt,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.auto_review_triggered, opt != "Off")
            self.assertEqual(r.slot1_sector_writes, 0)

    def test_93_86d_auto_review_never_triggers_in_movie_or_sq(self) -> None:
        for mode in ("Movie", "S&Q"):
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_auto_review_still_only_and_reset",
                shoot_mode=mode,
                auto_review_setting="10 Sec",
            )
            self.assertTrue(r.allowed)
            self.assertFalse(r.auto_review_triggered)

            r_req = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_auto_review_still_only_and_reset",
                shoot_mode=mode,
                auto_review_setting="10 Sec",
                trigger_auto_review_in_movie_requested=True,
            )
            self.assertFalse(r_req.allowed)
            self.assertEqual(r_req.errno, p376.EOPNOTSUPP_ERRNO)

    def test_94_86d_auto_review_resists_cam_reset_and_resets_on_initialize(self) -> None:
        r_rst = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_auto_review_still_only_and_reset",
            shoot_mode="Still",
            auto_review_setting="5 Sec",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertEqual(r_rst.auto_review_setting, "5 Sec")
        self.assertTrue(r_rst.setup_item_survived_cam_reset)

        r_init = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_auto_review_still_only_and_reset",
            shoot_mode="Still",
            auto_review_setting="5 Sec",
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertEqual(r_init.auto_review_setting, "Off")
        self.assertTrue(r_init.setup_item_reset_on_initialize)

    def test_95_86d_auto_review_invalid_setting_einval(self) -> None:
        r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_auto_review_still_only_and_reset",
            auto_review_setting="3 Sec",
        )
        self.assertEqual(r.errno, p376.EINVAL_ERRNO)

    def test_96_86d_fx6_zero_ibis_cleaning_zero_ir_zero_autoreview_eopnotsupp(self) -> None:
        r_cln = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_ibis_cleaning=True,
        )
        r_ir = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_ir_remote=True,
        )
        r_ar = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
            body_model=p376.BODY_MODEL_FX6,
            fx6_request_still_auto_review=True,
        )
        self.assertEqual(r_cln.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_cln.fx6_steadyshot_fixed_message, "The SteadyShot mechanism is fixed.")
        self.assertFalse(r_cln.fx6_has_ibis_cleaning)
        self.assertEqual(r_ir.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_ir.fx6_ir_remote_user_menus, 0)
        self.assertEqual(r_ar.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_ar.fx6_auto_review_user_menus, 0)

    def test_97_86d_fx6_rec_review_3_options_accepted_invalid_einval(self) -> None:
        for mode in p376.FX6_REC_REVIEW_OPTIONS:
            r = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
                body_model=p376.BODY_MODEL_FX6,
                fx6_rec_review_mode=mode,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.fx6_rec_review_mode, mode)
        r_bad = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
            body_model=p376.BODY_MODEL_FX6,
            fx6_rec_review_mode="Last 30s",
        )
        self.assertEqual(r_bad.errno, p376.EINVAL_ERRNO)

    def test_98_86d_cross_body_rejections_eopnotsupp(self) -> None:
        r1 = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
            body_model=p376.BODY_MODEL_FX6,
        )
        r2 = p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
            operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
            body_model=p376.BODY_MODEL_FX3,
        )
        self.assertEqual(r1.errno, p376.EOPNOTSUPP_ERRNO)
        self.assertEqual(r2.errno, p376.EOPNOTSUPP_ERRNO)

    def test_99_86d_invalid_dispatch_raises_stage86_error(self) -> None:
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(operation="bad_86d")
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
                body_model="FX9",
            )
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
                body_variant="ILME-FX3B",
            )
        with self.assertRaises(p376.Stage86Phase376Error):
            p376.simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
                operation="fx3_auto_review_still_only_and_reset",
                shoot_mode="Playback",
            )

    def test_100_86d_orchestrator_metrics_alignment(self) -> None:
        rep = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        s86d = rep["submodel_86d_cleaning_ir_autoreview_fx6_contrast"]
        self.assertTrue(s86d["passed"])
        self.assertEqual(s86d["fx3_sensor_cleaning_min_battery_pct"], 51)
        self.assertEqual(s86d["fx3_shutter_curtain_at_power_off"], "Open")
        self.assertEqual(s86d["fx3_dormant_antidust_exposed_events"], 0)
        self.assertEqual(s86d["fx3_auto_review_options_count"], 4)
        self.assertFalse(s86d["fx6_has_ibis_cleaning"])
        self.assertEqual(s86d["fx6_ir_remote_user_menus"], 0)
        self.assertEqual(s86d["fx6_auto_review_user_menus"], 0)

    # =========================================================================
    # Tests 101..108: 4-Mode Determinism, Portability, CLI & Suite 86/86 Wiring
    # =========================================================================

    def test_101_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            force_clean_room=True
        )
        r_f2 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["phase376_audit_digest_sha256"], r_f2["phase376_audit_digest_sha256"])
        self.assertEqual(r_f1["phase376_audit_digest_sha256"], r_f3["phase376_audit_digest_sha256"])

        r_dl1 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root=None
        )
        r_dl2 = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            work_root="/nonexistent/phase376_stage86_test"
        )
        self.assertEqual(r_dl1["phase376_audit_digest_sha256"], r_dl2["phase376_audit_digest_sha256"])

        r_norm = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["phase376_audit_digest_sha256"],
                r_f1["phase376_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase376_audit_digest_sha256"],
                r_dl1["phase376_audit_digest_sha256"],
            )

    def test_102_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p376.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_103_standalone_cli_self_test_summary_json_help_and_subprocess(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p376.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 376 Stage 86 (86/86)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p376.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "86/86")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p376.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("86/86", buf_help.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p376.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        self.assertIn("Phase 376 Stage 86 (86/86)", proc.stdout)

    def test_104_suite_default_config_and_forward_compatible_stage86_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_hil
        )
        self.assertTrue(default_cfg.include_stage86)
        self.assertTrue(
            default_cfg.stage86_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s86 = rep["stage86_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_hil"]
        self.assertTrue(s86["all_checks_passed"])
        self.assertEqual(s86["phase_number"], 376)
        self.assertEqual(s86["milestone"], "86/86")
        self.assertEqual(s86["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s86["slot1_data_sector_writes"], 0)
        self.assertEqual(s86["usb_tx_packets"], 0)
        self.assertEqual(s86["rf_tx_packets"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Forward-compatible assertion: Base 3 stages + optional phase flags >= 86
        self.assertGreaterEqual(len(stage_keys) + 3, 86)

    def test_105_suite_cli_summary_and_skip_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_hil=",
            buf.getvalue(),
        )
        self.assertIn("m86=86/86", buf.getvalue())

        for skip_flag in ("--skip-stage86", "--no-include-stage86", "--skip-phase376"):
            buf_skip = io.StringIO()
            with contextlib.redirect_stdout(buf_skip):
                rc_skip = suite.main([*_FAST_CLI_FLAGS, skip_flag, "--json"])
            self.assertEqual(rc_skip, 0)
            rep_skip = json.loads(buf_skip.getvalue())
            self.assertNotIn(
                "stage86_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_hil",
                rep_skip,
            )

    def test_106_suite_tamper_detection_fails_on_wrong_milestone(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            force_clean_room=True
        )
        with unittest.mock.patch.object(
            p376,
            "run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation",
            return_value={**real, "milestone": "85/85"},
        ):
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])

    def test_107_suite_tamper_detection_fails_on_redline_or_invariant_breach(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p376.run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
            force_clean_room=True
        )
        for bad_key, bad_val in (
            ("slot1_camset_write_authorized", True),
            ("fx3_dormant_slog2_exposed_events", 1),
            ("fx3_ipsec_v700_bypass_events", 1),
            ("fx6_has_ibis_cleaning", True),
            ("rf_tx_packets", 1),
            ("usb_tx_packets", 1),
        ):
            with unittest.mock.patch.object(
                p376,
                "run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation",
                return_value={**real, bad_key: bad_val},
            ):
                rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
                self.assertFalse(rep_bad["all_checks_passed"], f"Expected tamper fail for {bad_key}")

    def test_108_run_self_test_wrapper_passes_clean_room_and_donorless(self) -> None:
        r_cr = p376.run_self_test(force_clean_room=True)
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertEqual(r_cr["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        r_dl = p376.run_self_test(work_root=None)
        self.assertTrue(r_dl["all_checks_passed"])
        self.assertEqual(r_dl["source_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
