#!/usr/bin/env python3
"""Unit tests for Phase 333 (Stage 71 — 71/71 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-61:
- 71A: `[FTP Transfer Func.]` (`Server 1..9`, Passive-only `FTP`/`FTPES` vs dormant
  `SFTP`/Active/Implicit-990/`[Transfer JPEG/HEIF Size]` `EOPNOTSUPP=95`,
  `cacert.pem <= 1 MB` from Slot 1 root, `[FTP Function] = On` + `[Cloud Connection] = On`
  `EBUSY=16`, Zero-RF + `USB-LAN` bypass firewall, Slot-1 `save_ftp_transfer_list_to_media` /
  `AVF_INFO` recovery `0x0a13` `EROFS=30` vs FX6 `Server 1..3` Active+Passive / `Slot B`
  `certification.pem` / `Auto Upload (Proxy): Chunk`),
- 71B: `[White Balance]` (`2500K..9900K` 100K step, `Custom 1..3` `A7..B7 x G7..M7`
  CAMSET exclusion + Camera Reset internal survival + `Custom WB Error 0x0220`,
  `Cine EI` `Auto`/`Underwater Auto` lockout, Resettable `[Priority Set in AWB]` &
  Movie `[Shockless WB]` 0-frame direct dial bypass vs Initialize-only Still
  `[Shutter AWB Lock]` vs FX6 `PRST/A/B` / `Memory A..H` / `ATW Speed 1..5`),
- 71C: `[Movie AF & Focus Map]` (Shared `1..7` `[AF Transition Speed]` & `1..5`
  `[AF Subj. Shift Sensitivity]` on BOTH FX3 & FX6, rejecting `6/7`, Resettable
  `[AF Assist]` + `SELP1650`/`SEL18200LE` incompatibility, ZERO in-body `[Focus Map]`
  on FX3 vs Ver. 6.00+ external *Monitor & Control* telemetry `< 150fps` vs FX6
  native in-body `Focus Map` `> 6fps & < 150fps`),
- 71D: `[Marker Display]` & `[Peaking Display]` (15 active `Aspect Marker` ratios +
  `16:9` Ver. 3.00+ gate, `Safety Zone` `Off/80%/90%`, 4-Color `Peaking`
  `Red/Yellow/Blue/White`, all 8 items Initialize-only persistence, Clean-HDMI
  0-leak, `Focus Magnifier` auto-hide vs FX6 `Aspect Mask 0..15`, `User Box`
  `3..479 x 3..269`, and `B&W/Red/Yellow/Blue` Peaking) HIL
(96 four-mode tests).
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
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulator as p333  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..70 for quick Stage 71 isolation tests."""
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
]


class TestRealHwStage71FtpFtpesUsblanCustomWbAfFocusMapMarker(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & Dual-Mode Tests (Tests 1..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_71_of_71(self) -> None:
        self.assertEqual(p333.PHASE_NUMBER, 333)
        self.assertEqual(p333.STAGE_INDEX, 71)
        self.assertEqual(p333.STAGE_TOTAL, 71)
        self.assertEqual(p333.MILESTONE_LABEL, "71/71")
        self.assertTrue(p333.IS_71ST_STAGE_MILESTONE)
        self.assertEqual(
            p333.STAGE_NAME,
            "stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil",
        )
        self.assertEqual(len(p333.DONOR_RELPATHS), 19)
        self.assertEqual(len(p333.EXPECTED_DONOR_BYTES), 19)
        self.assertEqual(len(p333.EXPECTED_COMPACT_DONOR_SHA256), 16)
        self.assertEqual(len(p333.EXPECTED_LARGE_HEAD4K_SHA256), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p333.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p333.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p333.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p333.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p333.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p333.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p333.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p333.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p333.SLOT1_AVF_INFO_MUTATED)
        self.assertFalse(p333.FX3_HAS_INBODY_FOCUS_MAP)
        self.assertTrue(p333.FX6_HAS_INBODY_FOCUS_MAP)
        self.assertEqual(p333.FX3_FTP_MAX_SERVERS, 9)
        self.assertEqual(p333.FX6_FTP_MAX_SERVERS, 3)
        self.assertEqual(p333.FX3_MARKER_ACTIVE_RATIO_COUNT, 15)
        self.assertEqual(p333.PEAKING_COLOR_COUNT, 4)
        self.assertEqual(p333.RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(p333.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p333.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p333.clean_room_test_mode(env={}))
        self.assertTrue(p333.clean_room_test_mode(env={p333.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p333.clean_room_test_mode(env={p333.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p333.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p333.clean_room_test_mode(
                force_clean_room=False,
                env={p333.ENV_FORCE_CLEAN_ROOM: "1", p333.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_paths_none_fallback(self) -> None:
        self.assertIsNone(p333.resolve_phase333_donor_paths(None))
        self.assertIsNone(
            p333.resolve_mac_work_root(
                env={p333.ENV_MAC_WORK_ROOT: p333.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p333.resolve_mac_work_root(
                env={p333.ENV_MAC_ROOT: p333.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p333, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p333, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p333.resolve_mac_work_root(env={}))
                    self.assertIsNone(p333.resolve_phase333_donor_paths(None, env={}))
                    rep = p333.run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p333.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_19_contracts(self) -> None:
        for env_key in (p333.ENV_FORCE_CLEAN_ROOM, p333.ENV_CLEAN_ROOM_TEST):
            audit = p333.inspect_phase333_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p333.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p333.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 19)
            self.assertEqual(audit.compact_donors_verified, 16)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p333.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p333._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p333.inspect_phase333_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p333.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 19)
        self.assertEqual(audit.compact_donors_verified, 16)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_compact_donor_tokens_verified(self) -> None:
        self.assertEqual(p333.EXPECTED_DONOR_BYTES["fx3_lib_airplane"], 14_488)
        self.assertEqual(p333.EXPECTED_DONOR_BYTES["fx3_lib_bt"], 158_968)
        self.assertIn(b"Connects with FTPES.", p333.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Shockless WB", p333.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"AF Transition Speed", p333.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Aspect Marker", p333.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Custom WB Error", p333.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"File Transfer", p333.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"B&W", p333.COMPACT_DONOR_TOKENS["fx6_string_en_2"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p333._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p333.Stage71Phase333Error):
                p333._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p333.Stage71Phase333Error):
                p333._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p333.Stage71Phase333Error):
                p333._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p333.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p333._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p333.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_lib_airplane"] = "0" * 64
            with unittest.mock.patch.object(
                p333, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p333.inspect_phase333_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn(
                    "digest_or_size_mismatch:fx3_lib_airplane", audit.verification_notes
                )
        finally:
            p333._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p333.run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase333_payload_passes_clean_room(self) -> None:
        rep = p333.run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p333.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "71/71")
        self.assertTrue(rep["is_71st_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase333_payload_passes_local_donor_mode(self) -> None:
        if p333.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p333.run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p333.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 19)

    def test_13_fx3_large_windows_contain_wave61_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p333.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "BKID_FTP_SERVER_0_HOST",
            "BKID_FTP_SERVER_8_HOST",
            "SET_SERVER_SECURE_ON",
            "SAVE_FTP_TRANS_LIST",
            "CONTENT_FTP_COMPLETE",
            "PRM_HAITA_FTP_SLOT1_MEDIA",
            "USB_HOST_FUNCTION_USB_ETHER",
            "CLOUD_ON_FTP_OFF",
            "CTEMP_2500K",
            "CTEMP_9900K",
            "BKID_SHUTTER_AWB_LOCK",
            "BKID_SHOCKLESS_WB",
            "BKID_AF_TRANSITION_SPEED",
            "BKID_AF_SUBJ_SHIFT_SENS",
            "MOVIE_AF_TRANSITION_7_FAST",
            "MOVIE_AF_SENS_5",
            "REMOTE_EVT_FOCUS_MAP",
            "BKID_MARKER_DISPLAY",
            "MARKER_ASPECT_2_39_1",
            "BKID_PEAKING_COLOR",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_large_windows_contain_wave61_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p333.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "FX6_SET_SERVER_SFTP",
            "FX6_AUTO_UPLOAD_CHUNK",
            "FX6_WHITE_MEM_H",
            "FX6_ATW_SPEED_5",
            "FX6_MOVIE_AF_SENS_5",
            "FX6_USER_MENU_FOCUS_MAP",
            "FX6_USER_BOX",
            "FX6_PEAKING_B_W",
        ):
            self.assertIn(expected, labels)

    # ------------------------------------------------------------------
    # Sub-Model 71A — FTP/FTPES 9-Server, USB-LAN Bypass & Slot-1 EROFS (Tests 15..36)
    # ------------------------------------------------------------------

    def test_15_fx3_allows_servers_1_to_9_passive_ftp_and_ftpes(self) -> None:
        for proto in ("FTP", "FTPES"):
            for slot in (1, 5, 9):
                res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                    server_slot=slot,
                    protocol=proto,
                    transfer_mode="Passive",
                    zero_rf_bench_mode=False,
                    ftp_function="On",
                    connect_method="Wi-Fi",
                    airplane_mode="Off",
                )
                self.assertTrue(res.admitted, f"{proto} slot={slot}")
                self.assertEqual(res.max_servers, 9)

    def test_16_fx3_rejects_server_0_and_10_einval(self) -> None:
        for bad_slot in (0, 10):
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                server_slot=bad_slot,
                zero_rf_bench_mode=False,
            )
            self.assertFalse(res.admitted, bad_slot)
            self.assertEqual(res.errno_code, p333.EINVAL_ERRNO)

    def test_17_fx3_rejects_dormant_sftp_and_implicit_ftps_990_eopnotsupp(self) -> None:
        for bad_proto in ("SFTP", "FTPS_IMPLICIT_990"):
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                protocol=bad_proto,
                zero_rf_bench_mode=False,
            )
            self.assertFalse(res.admitted, bad_proto)
            self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_18_fx3_rejects_active_mode_passive_only_eopnotsupp(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            protocol="FTP",
            transfer_mode="Active",
            zero_rf_bench_mode=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_19_fx3_rejects_dormant_transfer_jpeg_heif_size_eopnotsupp(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            dormant_transfer_jpeg_heif_size_requested=True,
            zero_rf_bench_mode=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_20_fx3_cacert_pem_must_be_slot1_root_and_le_1mb(self) -> None:
        bad_name = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            cacert_filename="certification.pem",
            zero_rf_bench_mode=False,
        )
        self.assertFalse(bad_name.admitted)
        self.assertEqual(bad_name.errno_code, p333.EINVAL_ERRNO)

        bad_slot = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            cacert_source_slot="Slot 2",
            zero_rf_bench_mode=False,
        )
        self.assertFalse(bad_slot.admitted)
        self.assertEqual(bad_slot.errno_code, p333.EINVAL_ERRNO)

        too_big = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            cacert_size_bytes=p333.CACERT_MAX_BYTES + 1,
            zero_rf_bench_mode=False,
        )
        self.assertFalse(too_big.admitted)
        self.assertEqual(too_big.errno_code, p333.EINVAL_ERRNO)

        max_ok = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            cacert_size_bytes=p333.CACERT_MAX_BYTES,
            zero_rf_bench_mode=False,
        )
        self.assertTrue(max_ok.admitted)

    def test_21_fx3_ftp_function_mutually_exclusive_with_cloud_connection_ebusy(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            ftp_function="On",
            cloud_connection="On",
            zero_rf_bench_mode=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EBUSY_ERRNO)

    def test_22_bench_zero_exfil_passes_with_airplane_on_and_usblan_disabled(self) -> None:
        ok = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            airplane_mode="On",
            usb_lan_tethering_disabled=True,
            connect_method="Disabled",
            ftp_function="Off",
            zero_rf_bench_mode=True,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.usblan_airplane_bypass_detected)
        self.assertEqual(ok.rf_packets_transmitted, 0)
        self.assertEqual(ok.rf_nvs_mutation_bytes, 0)

    def test_23_usblan_under_airplane_mode_flagged_and_blocked_in_zero_rf_bench_eperm(self) -> None:
        for method in ("USB-LAN", "USB Tethering"):
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                airplane_mode="On",
                usb_lan_tethering_disabled=False,
                connect_method=method,
                ftp_function="On",
                zero_rf_bench_mode=True,
            )
            self.assertFalse(res.admitted, method)
            self.assertEqual(res.errno_code, p333.EPERM_ERRNO)
            self.assertTrue(res.usblan_airplane_bypass_detected)

    def test_24_airplane_off_blocked_in_zero_rf_bench_eperm(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            airplane_mode="Off",
            usb_lan_tethering_disabled=True,
            connect_method="Disabled",
            ftp_function="Off",
            zero_rf_bench_mode=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EPERM_ERRNO)

    def test_25_slot1_save_ftp_transfer_list_to_media_fails_closed_erofs_30(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            save_ftp_transfer_list_to_media_requested=True,
            target_slot=p333.SLOT_1,
            zero_rf_bench_mode=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EROFS_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_triggered)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_26_slot1_avf_info_recovery_0x0a13_fails_closed_erofs_30(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            avf_info_recovery_0x0a13_requested=True,
            target_slot=p333.SLOT_1,
            zero_rf_bench_mode=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EROFS_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_triggered)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_27_slot2_scratch_save_ftp_list_allowed_zero_slot1_writes(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            save_ftp_transfer_list_to_media_requested=True,
            target_slot=p333.SLOT_2,
            zero_rf_bench_mode=False,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.tier0_vault_firewall_triggered)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_28_ftp_survives_camera_reset_cleared_by_network_reset_and_init(self) -> None:
        cam_rst = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            ftp_function="On",
            connect_method="Wi-Fi",
            camera_settings_reset_applied=True,
            zero_rf_bench_mode=False,
        )
        self.assertTrue(cam_rst.admitted)
        self.assertEqual(cam_rst.effective_ftp_function, "On")

        net_rst = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            ftp_function="On",
            connect_method="Wi-Fi",
            reset_network_set_applied=True,
            zero_rf_bench_mode=True,
        )
        self.assertTrue(net_rst.admitted)
        self.assertEqual(net_rst.effective_ftp_function, "Off")

        init_rst = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            ftp_function="On",
            connect_method="Wi-Fi",
            initialize_applied=True,
            zero_rf_bench_mode=True,
        )
        self.assertTrue(init_rst.admitted)
        self.assertEqual(init_rst.effective_ftp_function, "Off")

    def test_29_ver700_clip_flag_filter_and_directory_hierarchy_prefix(self) -> None:
        same_cam = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            firmware_version=p333.FW_VER_702,
            directory_hierarchy="Same as in Camera",
            target_slot=p333.SLOT_2,
            clip_flag_filter="OK",
            zero_rf_bench_mode=False,
        )
        self.assertTrue(same_cam.admitted)
        self.assertEqual(same_cam.remote_path_prefix, "B/...")
        self.assertEqual(same_cam.clip_flag_filter, "OK")

        pre_700 = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            firmware_version=p333.FW_VER_600,
            clip_flag_filter="OK",
            zero_rf_bench_mode=False,
        )
        self.assertEqual(pre_700.clip_flag_filter, "Off")

    def test_30_fx6_3_servers_active_passive_and_slot_b_certification_pem(self) -> None:
        for mode in ("Active", "Passive"):
            ok = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                body_profile=p333.BODY_MODEL_FX6,
                server_slot=3,
                protocol="FTPES",
                transfer_mode=mode,
                fx6_auto_upload_proxy_chunk=True,
            )
            self.assertTrue(ok.admitted, mode)
            self.assertEqual(ok.max_servers, 3)
            self.assertEqual(ok.cacert_filename, "certification.pem")
            self.assertEqual(ok.cacert_source_slot, "Slot B")

        bad4 = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=p333.BODY_MODEL_FX6,
            server_slot=4,
        )
        self.assertFalse(bad4.admitted)
        self.assertEqual(bad4.errno_code, p333.EINVAL_ERRNO)

    def test_31_fx6_rejects_dormant_sftp_and_wrong_cert_or_chunk_conflict(self) -> None:
        sftp = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=p333.BODY_MODEL_FX6,
            protocol="SFTP",
        )
        self.assertFalse(sftp.admitted)
        self.assertEqual(sftp.errno_code, p333.EOPNOTSUPP_ERRNO)

        bad_cert = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            body_profile=p333.BODY_MODEL_FX6,
            cacert_filename="cacert.pem",
            cacert_source_slot="Slot 1",
        )
        self.assertFalse(bad_cert.admitted)
        self.assertEqual(bad_cert.errno_code, p333.EINVAL_ERRNO)

        for conflict in ("Simul Rec", "Relay Rec"):
            chunk_blk = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                body_profile=p333.BODY_MODEL_FX6,
                fx6_auto_upload_proxy_chunk=True,
                fx6_concurrent_conflict=conflict,
            )
            self.assertFalse(chunk_blk.admitted, conflict)
            self.assertEqual(chunk_blk.errno_code, p333.EBUSY_ERRNO)

    def test_32_fx3_clip_flag_filters_and_movie_raw_transfer_targets(self) -> None:
        for target in p333.VALID_MOVIE_FTP_TARGETS:
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                movie_transfer_target=target,
                zero_rf_bench_mode=False,
            )
            self.assertTrue(res.admitted, target)
        for target in p333.VALID_RAW_JH_TARGETS:
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                raw_jh_transfer_target=target,
                zero_rf_bench_mode=False,
            )
            self.assertTrue(res.admitted, target)

    def test_33_fx3_auto_ftp_targets_and_root_cert_policy(self) -> None:
        for auto_tgt in p333.VALID_AUTO_FTP_TARGETS:
            res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
                auto_ftp_transfer="On",
                auto_ftp_target=auto_tgt,
                root_cert_error_policy="Connect",
                zero_rf_bench_mode=False,
            )
            self.assertTrue(res.admitted, auto_tgt)

    def test_34_fx3_directory_hierarchy_standard_prefix_slash(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            directory_hierarchy="Standard",
            zero_rf_bench_mode=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.remote_path_prefix, "/")

    def test_35_fx3_usblan_disabled_false_with_disabled_method_still_flags_bypass(self) -> None:
        res = p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(
            airplane_mode="On",
            usb_lan_tethering_disabled=False,
            connect_method="Disabled",
            ftp_function="Off",
            zero_rf_bench_mode=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p333.EPERM_ERRNO)
        self.assertTrue(res.usblan_airplane_bypass_detected)

    def test_36_71a_invalid_inputs_raise_stage71_error(self) -> None:
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(body_profile="FX9")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(protocol="HTTP")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(connect_method="NFC")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_ftp_ftpes_usblan_zerorf_and_slot1_vault_hil(target_slot=3)

    # ------------------------------------------------------------------
    # Sub-Model 71B — WB 2500K..9900K, Custom 1..3, Shutter Lock, Shockless (Tests 37..54)
    # ------------------------------------------------------------------

    def test_37_wb_kelvin_bounds_and_100k_step_validated(self) -> None:
        for k in (2500, 3200, 5600, 9900):
            res = p333.simulate_white_balance_custom_shutter_shockless_hil(
                wb_mode="C.Temp./Filter",
                color_temp_k=k,
            )
            self.assertTrue(res.admitted, k)
        for bad_k in (2400, 5550, 10000):
            res = p333.simulate_white_balance_custom_shutter_shockless_hil(
                wb_mode="C.Temp./Filter",
                color_temp_k=bad_k,
            )
            self.assertFalse(res.admitted, bad_k)
            self.assertEqual(res.errno_code, p333.EINVAL_ERRNO)

    def test_38_wb_fine_tune_ab_half_step_and_gm_quarter_step_bounds(self) -> None:
        ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
            amber_blue_axis=-7.0,
            green_magenta_axis=6.75,
        )
        self.assertTrue(ok.admitted)
        for ab, gm in ((-7.5, 0.0), (0.25, 0.0), (0.0, 7.25), (0.0, 0.125)):
            bad = p333.simulate_white_balance_custom_shutter_shockless_hil(
                amber_blue_axis=ab,
                green_magenta_axis=gm,
            )
            self.assertFalse(bad.admitted, (ab, gm))
            self.assertEqual(bad.errno_code, p333.EINVAL_ERRNO)

    def test_39_custom13_excluded_from_camset_survives_camreset_wiped_on_init(self) -> None:
        rst = p333.simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Custom 1",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertFalse(rst.custom_wb_exported_in_camset)
        self.assertTrue(rst.custom_wb_internal_preserved_across_cam_reset)
        self.assertEqual(rst.effective_wb_mode, "Auto")

        init = p333.simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Custom 2",
            initialize_applied=True,
        )
        self.assertTrue(init.admitted)
        self.assertFalse(init.custom_wb_exported_in_camset)
        self.assertFalse(init.custom_wb_internal_preserved_across_cam_reset)

    def test_40_custom_setup_warns_0x0220_under_log_shooting_or_slog3_pplut(self) -> None:
        for log_mode, pp in (
            ("Flexible ISO", "Off"),
            ("Cine EI", "Off"),
            ("Cine EI Quick", "Off"),
            ("Off", "S-Log3"),
            ("Off", "PPLUT1"),
            ("Off", "PPLUT4"),
        ):
            res = p333.simulate_white_balance_custom_shutter_shockless_hil(
                wb_mode="Custom 1",
                log_shooting=log_mode,
                picture_profile=pp,
                custom_setup_capture_requested=True,
            )
            self.assertFalse(res.admitted, (log_mode, pp))
            self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.custom_wb_error_0x0220)

    def test_41_custom_setup_succeeds_when_log_off_and_non_log_pp(self) -> None:
        res = p333.simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Custom 3",
            log_shooting="Off",
            picture_profile="PP11",
            custom_setup_capture_requested=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.custom_wb_error_0x0220)

    def test_42_cine_ei_locks_out_auto_and_underwater_auto(self) -> None:
        for exp in ("Cine EI", "Cine EI Quick"):
            for bad_wb in ("Auto", "Underwater Auto"):
                res = p333.simulate_white_balance_custom_shutter_shockless_hil(
                    exposure_mode=exp,
                    wb_mode=bad_wb,
                )
                self.assertFalse(res.admitted, (exp, bad_wb))
                self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)
            ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
                exposure_mode=exp,
                wb_mode="C.Temp./Filter",
            )
            self.assertTrue(ok.admitted)

    def test_43_priority_set_in_awb_resettable_on_camera_settings_reset(self) -> None:
        for prio in p333.VALID_AWB_PRIORITIES:
            ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
                wb_mode="Auto",
                priority_set_in_awb=prio,
            )
            self.assertTrue(ok.admitted)
            self.assertEqual(ok.effective_priority_set_in_awb, prio)

        rst = p333.simulate_white_balance_custom_shutter_shockless_hil(
            wb_mode="Auto",
            priority_set_in_awb="White",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertEqual(rst.effective_priority_set_in_awb, "Standard")

    def test_44_shockless_wb_modes_and_0frame_bypass_on_direct_ctemp_dial(self) -> None:
        for mode, frames in (("Off", 0), ("1 (Fast)", 12), ("2", 30), ("3 (Slow)", 60)):
            ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
                shoot_mode=p333.SHOOT_MODE_MOVIE,
                shockless_wb=mode,
                direct_ctemp_or_filter_dial_edited=False,
            )
            self.assertTrue(ok.admitted, mode)
            self.assertEqual(ok.shockless_transition_frames, frames)

        bypass = p333.simulate_white_balance_custom_shutter_shockless_hil(
            shoot_mode=p333.SHOOT_MODE_MOVIE,
            shockless_wb="3 (Slow)",
            direct_ctemp_or_filter_dial_edited=True,
        )
        self.assertTrue(bypass.admitted)
        self.assertEqual(bypass.shockless_transition_frames, 0)

    def test_45_shockless_wb_resets_to_1_fast_on_camera_settings_reset(self) -> None:
        rst = p333.simulate_white_balance_custom_shutter_shockless_hil(
            shockless_wb="3 (Slow)",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertEqual(rst.effective_shockless_wb, "1 (Fast)")

    def test_46_shutter_awb_lock_still_only_and_survives_camera_reset(self) -> None:
        ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
            shoot_mode=p333.SHOOT_MODE_STILL,
            shutter_awb_lock="Shut. Halfway",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_shutter_awb_lock, "Shut. Halfway")

        init = p333.simulate_white_balance_custom_shutter_shockless_hil(
            shoot_mode=p333.SHOOT_MODE_STILL,
            shutter_awb_lock="Cont. Shooting",
            initialize_applied=True,
        )
        self.assertTrue(init.admitted)
        self.assertEqual(init.effective_shutter_awb_lock, "Off")

    def test_47_shutter_awb_lock_rejected_in_movie_and_sq_modes(self) -> None:
        for mode in (p333.SHOOT_MODE_MOVIE, p333.SHOOT_MODE_SQ):
            bad = p333.simulate_white_balance_custom_shutter_shockless_hil(
                shoot_mode=mode,
                shutter_awb_lock="Shut. Halfway",
            )
            self.assertFalse(bad.admitted, mode)
            self.assertEqual(bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_48_fx3_rejects_fx6_only_wb_modes(self) -> None:
        for fx6_wb in p333.FX6_EXTRA_WB_MODES:
            bad = p333.simulate_white_balance_custom_shutter_shockless_hil(
                body_profile=p333.BODY_MODEL_FX3,
                wb_mode=fx6_wb,
            )
            self.assertFalse(bad.admitted, fx6_wb)
            self.assertEqual(bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_49_fx6_prst_a_b_memory_a_to_h_and_atw_speed_1_to_5(self) -> None:
        for sw, wb in (("PRST", "Preset 5600K"), ("A", "Memory A"), ("B", "Memory H")):
            ok = p333.simulate_white_balance_custom_shutter_shockless_hil(
                body_profile=p333.BODY_MODEL_FX6,
                fx6_wht_bal_switch=sw,
                wb_mode=wb,
            )
            self.assertTrue(ok.admitted, (sw, wb))

        atw = p333.simulate_white_balance_custom_shutter_shockless_hil(
            body_profile=p333.BODY_MODEL_FX6,
            fx6_wht_bal_switch="A",
            wb_mode="ATW",
            fx6_atw_speed=5,
        )
        self.assertTrue(atw.admitted)
        self.assertEqual(atw.fx6_atw_speed, 5)

    def test_50_fx6_cine_ei_locks_out_atw_and_invalid_atw_speed_einval(self) -> None:
        ei = p333.simulate_white_balance_custom_shutter_shockless_hil(
            body_profile=p333.BODY_MODEL_FX6,
            exposure_mode="Cine EI",
            wb_mode="ATW",
        )
        self.assertFalse(ei.admitted)
        self.assertEqual(ei.errno_code, p333.EOPNOTSUPP_ERRNO)

        for bad_spd in (0, 6):
            spd = p333.simulate_white_balance_custom_shutter_shockless_hil(
                body_profile=p333.BODY_MODEL_FX6,
                wb_mode="ATW",
                fx6_atw_speed=bad_spd,
            )
            self.assertFalse(spd.admitted, bad_spd)
            self.assertEqual(spd.errno_code, p333.EINVAL_ERRNO)

    def test_51_fx6_lacks_still_only_shutter_awb_lock(self) -> None:
        bad = p333.simulate_white_balance_custom_shutter_shockless_hil(
            body_profile=p333.BODY_MODEL_FX6,
            shutter_awb_lock="Shut. Halfway",
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_52_all_15_fx3_wb_modes_admitted_in_normal_shooting(self) -> None:
        for wb in p333.FX3_STANDARD_WB_MODES:
            res = p333.simulate_white_balance_custom_shutter_shockless_hil(wb_mode=wb)
            self.assertTrue(res.admitted, wb)

    def test_53_cine_ei_reset_defaults_effective_wb_to_ctemp_filter(self) -> None:
        res = p333.simulate_white_balance_custom_shutter_shockless_hil(
            exposure_mode="Cine EI",
            wb_mode="Daylight",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_wb_mode, "C.Temp./Filter")

    def test_54_71b_invalid_inputs_raise_stage71_error(self) -> None:
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_white_balance_custom_shutter_shockless_hil(wb_mode="MatrixWB")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_white_balance_custom_shutter_shockless_hil(priority_set_in_awb="Warm")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_white_balance_custom_shutter_shockless_hil(shockless_wb="4")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_white_balance_custom_shutter_shockless_hil(fx6_wht_bal_switch="C")

    # ------------------------------------------------------------------
    # Sub-Model 71C — Movie AF 1..7 / 1..5 Scales, AF Assist & Focus Map (Tests 55..70)
    # ------------------------------------------------------------------

    def test_55_fx3_and_fx6_both_allow_af_transition_speed_1_to_7(self) -> None:
        for body in (p333.BODY_MODEL_FX3, p333.BODY_MODEL_FX6):
            for spd in (1, 5, 7):
                res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                    body_profile=body,
                    af_transition_speed=spd,
                )
                self.assertTrue(res.admitted, (body, spd))
                self.assertEqual(res.effective_af_transition_speed, spd)
            for bad in (0, 8):
                bad_res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                    body_profile=body,
                    af_transition_speed=bad,
                )
                self.assertFalse(bad_res.admitted, (body, bad))
                self.assertEqual(bad_res.errno_code, p333.EINVAL_ERRNO)

    def test_56_fx3_and_fx6_both_strictly_cap_af_subj_shift_sensitivity_1_to_5(self) -> None:
        for body in (p333.BODY_MODEL_FX3, p333.BODY_MODEL_FX6):
            for sens in (1, 3, 5):
                res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                    body_profile=body,
                    af_subj_shift_sensitivity=sens,
                )
                self.assertTrue(res.admitted, (body, sens))
                self.assertEqual(res.effective_af_subj_shift_sensitivity, sens)
            for bad in (0, 6, 7):
                bad_res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                    body_profile=body,
                    af_subj_shift_sensitivity=bad,
                )
                self.assertFalse(bad_res.admitted, (body, bad))
                self.assertEqual(bad_res.errno_code, p333.EINVAL_ERRNO)

    def test_57_af_params_all_reset_on_camera_settings_reset_and_initialize(self) -> None:
        for kwargs in (
            dict(camera_settings_reset_applied=True),
            dict(initialize_applied=True),
        ):
            res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                af_transition_speed=2,
                af_subj_shift_sensitivity=1,
                af_assist="On",
                **kwargs,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_af_transition_speed, 5)
            self.assertEqual(res.effective_af_subj_shift_sensitivity, 5)
            self.assertEqual(res.effective_af_assist, "Off")

    def test_58_af_assist_requires_movie_or_sq_with_af_c(self) -> None:
        for mode in (p333.SHOOT_MODE_MOVIE, p333.SHOOT_MODE_SQ):
            ok = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                shoot_mode=mode,
                focus_mode="AF-C",
                af_assist="On",
            )
            self.assertTrue(ok.admitted, mode)

        still_bad = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
            shoot_mode=p333.SHOOT_MODE_STILL,
            focus_mode="AF-C",
            af_assist="On",
        )
        self.assertFalse(still_bad.admitted)
        self.assertEqual(still_bad.errno_code, p333.EOPNOTSUPP_ERRNO)

        mf_bad = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
            shoot_mode=p333.SHOOT_MODE_MOVIE,
            focus_mode="MF",
            af_assist="On",
        )
        self.assertFalse(mf_bad.admitted)
        self.assertEqual(mf_bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_59_af_assist_rejects_selp1650_sel18200le_and_non_pdaf(self) -> None:
        for lens in p333.AF_ASSIST_INCOMPATIBLE_LENSES:
            bad = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                shoot_mode=p333.SHOOT_MODE_MOVIE,
                focus_mode="AF-C",
                af_assist="On",
                lens_model=lens,
            )
            self.assertFalse(bad.admitted, lens)
            self.assertEqual(bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_60_fx3_has_zero_inbody_focus_map_always_eopnotsupp(self) -> None:
        res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
            body_profile=p333.BODY_MODEL_FX3,
            firmware_version=p333.FW_VER_702,
            inbody_focus_map_requested=True,
        )
        self.assertFalse(res.admitted)
        self.assertFalse(res.inbody_focus_map_supported)
        self.assertEqual(res.errno_code, p333.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.recorded_or_hdmi_focus_map_pixels, 0)

    def test_61_fx3_external_mc_focus_map_requires_ver_600_plus(self) -> None:
        for old_fw in (p333.FW_VER_200, p333.FW_VER_300, p333.FW_VER_400, p333.FW_VER_500):
            old_res = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                firmware_version=old_fw,
                external_mc_focus_map_requested=True,
                fps=59.94,
            )
            self.assertFalse(old_res.admitted, old_fw)
            self.assertEqual(old_res.errno_code, p333.EOPNOTSUPP_ERRNO)

        for new_fw in (p333.FW_VER_600, p333.FW_VER_700, p333.FW_VER_702):
            ok = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                firmware_version=new_fw,
                external_mc_focus_map_requested=True,
                fps=119.88,
            )
            self.assertTrue(ok.admitted, new_fw)
            self.assertTrue(ok.external_mc_focus_map_active)
            self.assertEqual(ok.recorded_or_hdmi_focus_map_pixels, 0)

    def test_62_fx3_external_mc_focus_map_blocked_at_150fps_200fps_240fps_sq(self) -> None:
        for high_fps in (150.0, 200.0, 240.0):
            blk = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                external_mc_focus_map_requested=True,
                fps=high_fps,
                sq_mode_active=True,
            )
            self.assertFalse(blk.admitted, high_fps)
            self.assertFalse(blk.external_mc_focus_map_active)
            self.assertEqual(blk.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_63_fx3_external_mc_focus_map_blocked_by_autoframing_playback_mf_usb_remote(self) -> None:
        for kwargs in (
            dict(auto_framing_active=True),
            dict(playback_control_active=True),
            dict(focus_mode="MF"),
            dict(lens_model="Non_PDAF_Adapter"),
            dict(lens_model="No_Lens"),
            dict(usb_wired_remote_or_uvc_active=True),
        ):
            blk = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                external_mc_focus_map_requested=True,
                fps=23.98,
                **kwargs,
            )
            self.assertFalse(blk.admitted, kwargs)
            self.assertFalse(blk.external_mc_focus_map_active)
            self.assertEqual(blk.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_64_fx6_native_inbody_focus_map_allowed_gt_6fps_and_lt_150fps(self) -> None:
        for fps in (23.98, 59.94, 119.88):
            ok = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                body_profile=p333.BODY_MODEL_FX6,
                inbody_focus_map_requested=True,
                fps=fps,
            )
            self.assertTrue(ok.admitted, fps)
            self.assertTrue(ok.inbody_focus_map_supported)

    def test_65_fx6_native_inbody_focus_map_blocked_le_6fps_or_ge_150fps(self) -> None:
        for fps in (1.0, 6.0, 150.0, 240.0):
            blk = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                body_profile=p333.BODY_MODEL_FX6,
                inbody_focus_map_requested=True,
                fps=fps,
            )
            self.assertFalse(blk.admitted, fps)
            self.assertEqual(blk.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_66_fx6_native_focus_map_blocked_during_hdmi_raw_mag_or_extender(self) -> None:
        for flag in (
            "fx6_hdmi_raw_active",
            "fx6_focus_magnifier_active",
            "fx6_digital_extender_active",
        ):
            blk = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                body_profile=p333.BODY_MODEL_FX6,
                inbody_focus_map_requested=True,
                fps=23.98,
                **{flag: True},
            )
            self.assertFalse(blk.admitted, flag)
            self.assertEqual(blk.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_67_fx3_af_assist_allowed_in_sq_mode_with_sel2470gm2(self) -> None:
        ok = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
            shoot_mode=p333.SHOOT_MODE_SQ,
            focus_mode="AF-C",
            af_assist="On",
            lens_model="SEL2470GM2",
            sq_mode_active=True,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_af_assist, "On")

    def test_68_fx3_af_assist_blocked_under_dmf_or_afs(self) -> None:
        for fm in ("AF-S", "AF-A", "DMF"):
            blk = p333.simulate_movie_af_scales_assist_and_focusmap_hil(
                shoot_mode=p333.SHOOT_MODE_MOVIE,
                focus_mode=fm,
                af_assist="On",
            )
            self.assertFalse(blk.admitted, fm)
            self.assertEqual(blk.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_69_fx3_af_transition_speed_and_shift_sens_defaults_5(self) -> None:
        res = p333.simulate_movie_af_scales_assist_and_focusmap_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_af_transition_speed, 5)
        self.assertEqual(res.effective_af_subj_shift_sensitivity, 5)
        self.assertEqual(res.effective_af_assist, "Off")

    def test_70_71c_invalid_inputs_raise_stage71_error(self) -> None:
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_movie_af_scales_assist_and_focusmap_hil(af_assist="Auto")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_movie_af_scales_assist_and_focusmap_hil(focus_mode="CAF")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_movie_af_scales_assist_and_focusmap_hil(lens_model="XYZ")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_movie_af_scales_assist_and_focusmap_hil(firmware_version="9.99")

    # ------------------------------------------------------------------
    # Sub-Model 71D — 15-Ratio Marker & 4-Color Peaking Clean-HDMI HIL (Tests 71..84)
    # ------------------------------------------------------------------

    def test_71_fx3_all_15_active_aspect_marker_ratios_plus_off_equal_16_states(self) -> None:
        self.assertEqual(len(p333.FX3_ACTIVE_ASPECT_MARKER_RATIOS), 15)
        self.assertEqual(len(p333.VALID_ASPECT_MARKER_STATES), 16)
        for ratio in p333.VALID_ASPECT_MARKER_STATES:
            res = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                firmware_version=p333.FW_VER_702,
                marker_display="On",
                aspect_marker=ratio,
            )
            self.assertTrue(res.admitted, ratio)
            self.assertEqual(res.effective_aspect_marker, ratio)
            self.assertEqual(res.hdmi_marker_or_peaking_leaked_pixels, 0)

    def test_72_fx3_aspect_16_9_requires_ver_300_plus_blocked_on_ver_200(self) -> None:
        old = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            firmware_version=p333.FW_VER_200,
            marker_display="On",
            aspect_marker="16:9",
        )
        self.assertFalse(old.admitted)
        self.assertEqual(old.errno_code, p333.EOPNOTSUPP_ERRNO)

        v300 = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            firmware_version=p333.FW_VER_300,
            marker_display="On",
            aspect_marker="16:9",
        )
        self.assertTrue(v300.admitted)

    def test_73_fx3_4_peaking_colors_vs_fx6_bw_rejection(self) -> None:
        self.assertEqual(p333.FX3_PEAKING_COLORS, ("Red", "Yellow", "Blue", "White"))
        for color in p333.FX3_PEAKING_COLORS:
            res = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                peaking_display="On",
                peaking_level="High",
                peaking_color=color,
            )
            self.assertTrue(res.admitted, color)
            self.assertEqual(res.effective_peaking_color, color)
            self.assertFalse(res.hdmi_peaking_overlay_active)

        bw = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            body_profile=p333.BODY_MODEL_FX3,
            peaking_display="On",
            peaking_color="B&W",
        )
        self.assertFalse(bw.admitted)
        self.assertEqual(bw.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_74_fx3_safety_zone_off_80_90_vs_fx6_925_95_rejected(self) -> None:
        for sz in ("Off", "80%", "90%"):
            ok = p333.simulate_marker_15ratio_and_peaking_4color_hil(safety_zone=sz)
            self.assertTrue(ok.admitted, sz)
        for bad_sz in ("92.5%", "95%"):
            bad = p333.simulate_marker_15ratio_and_peaking_4color_hil(safety_zone=bad_sz)
            self.assertFalse(bad.admitted, bad_sz)
            self.assertEqual(bad.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_75_all_8_marker_and_peaking_items_survive_camera_settings_reset(self) -> None:
        rst = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            marker_display="On",
            center_marker="On",
            aspect_marker="2.39:1",
            safety_zone="90%",
            guideframe="On",
            peaking_display="On",
            peaking_level="High",
            peaking_color="Red",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertTrue(rst.all_8_items_survive_camera_settings_reset)
        self.assertEqual(rst.effective_marker_display, "On")
        self.assertEqual(rst.effective_center_marker, "On")
        self.assertEqual(rst.effective_aspect_marker, "2.39:1")
        self.assertEqual(rst.effective_safety_zone, "90%")
        self.assertEqual(rst.effective_guideframe, "On")
        self.assertEqual(rst.effective_peaking_display, "On")
        self.assertEqual(rst.effective_peaking_level, "High")
        self.assertEqual(rst.effective_peaking_color, "Red")

    def test_76_all_8_marker_and_peaking_items_reset_on_initialize(self) -> None:
        init = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            marker_display="On",
            center_marker="On",
            aspect_marker="9:16",
            safety_zone="80%",
            guideframe="On",
            peaking_display="On",
            peaking_level="Low",
            peaking_color="Blue",
            initialize_applied=True,
        )
        self.assertTrue(init.admitted)
        self.assertEqual(init.effective_marker_display, "Off")
        self.assertEqual(init.effective_center_marker, "Off")
        self.assertEqual(init.effective_aspect_marker, "Off")
        self.assertEqual(init.effective_safety_zone, "Off")
        self.assertEqual(init.effective_guideframe, "Off")
        self.assertEqual(init.effective_peaking_display, "Off")
        self.assertEqual(init.effective_peaking_level, "Mid")
        self.assertEqual(init.effective_peaking_color, "White")

    def test_77_marker_display_auto_hides_during_focus_magnifier(self) -> None:
        mag = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            marker_display="On",
            aspect_marker="2.39:1",
            focus_magnifier_active=True,
        )
        self.assertTrue(mag.admitted)
        self.assertTrue(mag.marker_auto_hidden_for_magnifier)
        self.assertFalse(mag.effective_marker_overlay_visible)
        self.assertEqual(mag.effective_marker_display, "On")

    def test_78_marker_display_movie_and_sq_only_still_rejected_eopnotsupp(self) -> None:
        still = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            shoot_mode=p333.SHOOT_MODE_STILL,
            marker_display="On",
        )
        self.assertFalse(still.admitted)
        self.assertEqual(still.errno_code, p333.EOPNOTSUPP_ERRNO)

        sq = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            shoot_mode=p333.SHOOT_MODE_SQ,
            marker_display="On",
            aspect_marker="4:5",
        )
        self.assertTrue(sq.admitted)

    def test_79_peaking_display_also_allowed_in_still_mode_and_clean_hdmi_zero_leak(self) -> None:
        still_pk = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            shoot_mode=p333.SHOOT_MODE_STILL,
            marker_display="Off",
            peaking_display="On",
            peaking_color="Yellow",
        )
        self.assertTrue(still_pk.admitted)
        self.assertEqual(still_pk.hdmi_marker_or_peaking_leaked_pixels, 0)
        self.assertFalse(still_pk.hdmi_marker_overlay_active)
        self.assertFalse(still_pk.hdmi_peaking_overlay_active)

    def test_80_fx6_aspect_mask_0_to_15_and_bounds(self) -> None:
        for mask in (0, 12, 15):
            ok = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                body_profile=p333.BODY_MODEL_FX6,
                fx6_aspect_mask_level=mask,
            )
            self.assertTrue(ok.admitted, mask)
        for bad_mask in (-1, 16):
            bad = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                body_profile=p333.BODY_MODEL_FX6,
                fx6_aspect_mask_level=bad_mask,
            )
            self.assertFalse(bad.admitted, bad_mask)
            self.assertEqual(bad.errno_code, p333.EINVAL_ERRNO)

    def test_81_fx6_user_box_3_to_479_x_3_to_269_and_position_bounds(self) -> None:
        ok = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            body_profile=p333.BODY_MODEL_FX6,
            fx6_user_box_width=479,
            fx6_user_box_height=269,
            fx6_user_box_h_pos=-476,
            fx6_user_box_v_pos=266,
        )
        self.assertTrue(ok.admitted)

        for bad_kwargs in (
            dict(fx6_user_box_width=2),
            dict(fx6_user_box_width=480),
            dict(fx6_user_box_height=2),
            dict(fx6_user_box_height=270),
            dict(fx6_user_box_h_pos=477),
            dict(fx6_user_box_v_pos=-267),
        ):
            bad = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                body_profile=p333.BODY_MODEL_FX6,
                **bad_kwargs,
            )
            self.assertFalse(bad.admitted, bad_kwargs)
            self.assertEqual(bad.errno_code, p333.EINVAL_ERRNO)

    def test_82_fx6_peaking_colors_bw_red_yellow_blue_vs_white_rejected(self) -> None:
        for color in p333.FX6_PEAKING_COLORS:
            ok = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                body_profile=p333.BODY_MODEL_FX6,
                peaking_display="On",
                peaking_color=color,
            )
            self.assertTrue(ok.admitted, color)
        white = p333.simulate_marker_15ratio_and_peaking_4color_hil(
            body_profile=p333.BODY_MODEL_FX6,
            peaking_display="On",
            peaking_color="White",
        )
        self.assertFalse(white.admitted)
        self.assertEqual(white.errno_code, p333.EOPNOTSUPP_ERRNO)

    def test_83_fx3_peaking_levels_high_mid_low_all_admitted(self) -> None:
        for lvl in p333.VALID_PEAKING_LEVELS:
            ok = p333.simulate_marker_15ratio_and_peaking_4color_hil(
                peaking_display="On",
                peaking_level=lvl,
                peaking_color="White",
            )
            self.assertTrue(ok.admitted, lvl)
            self.assertEqual(ok.effective_peaking_level, lvl)

    def test_84_71d_invalid_inputs_raise_stage71_error(self) -> None:
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_marker_15ratio_and_peaking_4color_hil(aspect_marker="3:2")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_marker_15ratio_and_peaking_4color_hil(safety_zone="75%")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_marker_15ratio_and_peaking_4color_hil(peaking_level="Max")
        with self.assertRaises(p333.Stage71Phase333Error):
            p333.simulate_marker_15ratio_and_peaking_4color_hil(peaking_color="Green")

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 71 Wiring (Tests 85..96)
    # ------------------------------------------------------------------

    def test_85_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("71/71", proc.stdout)

    def test_86_suite_cli_help_percent_escaping_and_stage71_flags(self) -> None:
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
        self.assertIn("71/71 Milestone", proc.stdout)
        self.assertIn("--include-stage71", proc.stdout)
        self.assertIn("--skip-stage71", proc.stdout)
        self.assertIn("--no-include-stage71", proc.stdout)
        self.assertIn("--skip-phase333", proc.stdout)

    def test_87_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p333.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 333 Stage 71 (71/71 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p333.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "71/71")
        self.assertTrue(parsed["is_71st_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_88_no_hardcoded_usr_bin_python3_in_stage71_files(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_89_suite_default_config_enables_stage71_and_full_run_contains_71_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase333_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil
        )
        self.assertTrue(cfg.include_stage71)
        self.assertTrue(
            cfg.stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 71)
        s71 = rep["stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil"]
        self.assertTrue(s71["all_checks_passed"])
        self.assertTrue(s71["is_71st_stage_milestone"])
        self.assertEqual(s71["milestone"], "71/71")
        self.assertEqual(s71["phase_number"], 333)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_90_suite_skip_flags_and_summary_cli_for_stage71(self) -> None:
        for flag in ("--skip-stage71", "--no-include-stage71", "--skip-phase333"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage71"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage71", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil=CLEAN_ROOM_SYNTHETIC("
            "m71=71/71,srv=9/3,usblan_byp=0,wb_leak=0,fmap_ib=0,mrk_rat=15,"
            "hdmi_px=0,rf_tx=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_91_suite_tamper_71a_ftp_usblan_or_slot1_bypass_detected(self) -> None:
        for attr, val in (
            ("FX3_FTP_MAX_SERVERS", 3),
            ("FX6_FTP_MAX_SERVERS", 9),
            ("DORMANT_SFTP_EXPOSED_EVENTS", 1),
            ("ACTIVE_FTP_OR_IMPLICIT_FTPS_BYPASS_EVENTS", 1),
            ("DORMANT_TRANSFER_JPEG_HEIF_SIZE_EXPOSED_EVENTS", 1),
            ("USBLAN_ZERO_RF_BYPASS_EVENTS", 1),
            ("FTP_CLOUD_MUTUAL_EXCLUSION_VIOLATIONS", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("SLOT1_VAULT_FTP_MUTATION_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p333, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_71b_wb_camset_cine_ei_or_shockless_detected(self) -> None:
        for attr, val in (
            ("CUSTOM_WB_CAMSET_LEAK_EVENTS", 1),
            ("CINE_EI_AUTO_WB_BYPASS_EVENTS", 1),
            ("SHOCKLESS_WB_DIRECT_CTEMP_LAG_FRAMES", 1),
        ):
            with unittest.mock.patch.object(p333, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_suite_tamper_71c_af_scales_or_focus_map_detected(self) -> None:
        for attr, val in (
            ("FX3_HAS_INBODY_FOCUS_MAP", True),
            ("FX6_HAS_INBODY_FOCUS_MAP", False),
            ("INBODY_FOCUS_MAP_EXPOSED_EVENTS", 1),
            ("FOCUS_MAP_150FPS_OR_AUTOFRAMING_BYPASS_EVENTS", 1),
            ("AF_SUBJ_SHIFT_6_7_SPOOF_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p333, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_94_suite_tamper_71d_marker_15ratio_hdmi_or_magnifier_detected(self) -> None:
        for attr, val in (
            ("FX3_MARKER_ACTIVE_RATIO_COUNT", 14),
            ("HDMI_MARKER_OR_PEAKING_LEAKED_PIXELS", 1),
            ("CAMERA_RESET_MARKER_OR_PEAKING_WIPE_EVENTS", 1),
            ("MARKER_FOCUS_MAGNIFIER_COLLISION_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p333, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_95_suite_tamper_hard_write_and_rf_redlines_detected(self) -> None:
        for attr, val in (
            ("PERSISTENT_EMMC_WRITES_AUTHORIZED", True),
            ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True),
            ("PHYSICAL_DEVICE_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RF_PACKETS_TRANSMITTED", 1),
            ("RF_NVS_MUTATION_BYTES", 16),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
        ):
            with unittest.mock.patch.object(p333, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_96_stage71_all_redline_zero_keys_verified(self) -> None:
        rep = p333.run_phase333_ftp_ftpes_usblan_customwb_af_focusmap_marker_coemulation(
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
            "dormant_sftp_exposed_events",
            "active_ftp_or_implicit_ftps_bypass_events",
            "dormant_transfer_jpeg_heif_size_exposed_events",
            "usblan_zero_rf_bypass_events",
            "ftp_cloud_mutual_exclusion_violations",
            "slot1_data_sector_writes",
            "slot1_vault_ftp_mutation_events",
            "custom_wb_camset_leak_events",
            "cine_ei_auto_wb_bypass_events",
            "shockless_wb_direct_ctemp_lag_frames",
            "inbody_focus_map_exposed_events",
            "focus_map_150fps_or_autoframing_bypass_events",
            "af_subj_shift_6_7_spoof_events",
            "hdmi_marker_or_peaking_leaked_pixels",
            "camera_reset_marker_or_peaking_wipe_events",
            "marker_focus_magnifier_collision_events",
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
