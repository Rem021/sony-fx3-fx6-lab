#!/usr/bin/env python3
"""Unit tests for Phase 330 (Stage 70 — 70/70 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-60:
`[Rec. Media Settings]` (Removed `[Prioritize Rec. Media]` `EOPNOTSUPP=95`,
Initialize-Only `[Recording Media]` Still 4 vs Movie 3 + `[Auto Switch Media]`,
`Simult. Recording` Filesystem Parity, CRITICAL `Slot-2 -> Slot-1` Overflow Trap
Dual-Lock `EROFS=30`, `VPG200/VPG400` vs `SDXC V60/V90` Speed Gates vs `ILME-FX6`
`Simul Rec`/`Rec Button Set`/`Relay Rec` Exclusions),
`[Proxy Settings]` (`sq_proxy`: `XAVC S HD 6M 8bit` vs `XAVC HS HD 9M/16M 10bit`,
Allowed on `XAVC S-I DCI 4K <=59.94p`, Cutoff at `100p/119.88p/120fps+`,
`/PRIVATE/M4ROOT/SUB/*S03.MP4` vs `/M4ROOT/SUB/*S03.MP4` Non-Playable In-Camera &
Coupled Delete/Protect + `Slot-1` Vault `EROFS=30` vs `ILME-FX6` `1920x1080 9Mbps AVC`
+ `Chunk` Proxy Slot B),
`[Creators' Cloud]` / `[C3 Portal]` (`Cloud Connection *` & `Cloud Information *`
Surviving BOTH `[Camera Settings Reset]` AND `[Initialize]`, Ver. 7.00+ `Clip Flag`,
CRITICAL Power-OFF BLE Zero-RF 3-Lock Guard vs Zero-Bluetooth `ILME-FX6`), and
`[My Menu]` (Exact `6 pages x 7 items = 42` Slots `BKID_APP_mymenu_group{1..6}_setting_list{0..6}`,
Rejecting `group0/group7/list7` `EINVAL=22` & `(Playback)` `EOPNOTSUPP=95`,
Surviving `[Camera Settings Reset]` vs `ILME-FX6` `20`-Item `User Menu` +
`User Menu Only` + `User Menu with Lock` `0000..9999` 4-Digit PIN Excluded from
`All File` & `Scene File`) HIL
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
import realhw_rec_media_autoswitch_proxy_cloud_mymenu_coemulator as p330  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..69 for quick Stage 70 isolation tests."""
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
]


class TestRealHwStage70RecMediaAutoSwitchProxyCloudMyMenu(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & Dual-Mode Tests (Tests 1..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_70_of_70(self) -> None:
        self.assertEqual(p330.PHASE_NUMBER, 330)
        self.assertEqual(p330.STAGE_INDEX, 70)
        self.assertEqual(p330.STAGE_TOTAL, 70)
        self.assertEqual(p330.MILESTONE_LABEL, "70/70")
        self.assertTrue(p330.IS_70TH_STAGE_MILESTONE)
        self.assertEqual(
            p330.STAGE_NAME,
            "stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil",
        )
        self.assertEqual(len(p330.DONOR_RELPATHS), 19)
        self.assertEqual(len(p330.EXPECTED_DONOR_BYTES), 19)
        self.assertEqual(len(p330.EXPECTED_COMPACT_DONOR_SHA256), 16)
        self.assertEqual(len(p330.EXPECTED_LARGE_HEAD4K_SHA256), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p330.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p330.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p330.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p330.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p330.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p330.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p330.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p330.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p330.SLOT1_AVF_INFO_MUTATED)
        self.assertFalse(p330.FX6_BLUETOOTH_HARDWARE_PRESENT)
        self.assertEqual(p330.MYMENU_EXACT_SLOT_CAPACITY, 42)
        self.assertEqual(p330.FX6_USER_MENU_CAPACITY, 20)
        self.assertEqual(p330.RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(p330.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p330.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p330.clean_room_test_mode(env={}))
        self.assertTrue(p330.clean_room_test_mode(env={p330.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p330.clean_room_test_mode(env={p330.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p330.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p330.clean_room_test_mode(
                force_clean_room=False,
                env={p330.ENV_FORCE_CLEAN_ROOM: "1", p330.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_sentinel_and_donorless_fallback_no_typeerror(self) -> None:
        self.assertIsNone(
            p330.resolve_mac_work_root(
                env={p330.ENV_MAC_WORK_ROOT: p330.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p330.resolve_mac_work_root(
                env={p330.ENV_MAC_ROOT: p330.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p330, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p330, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p330.resolve_mac_work_root(env={}))
                    rep = p330.run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p330.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_19_contracts(self) -> None:
        for env_key in (p330.ENV_FORCE_CLEAN_ROOM, p330.ENV_CLEAN_ROOM_TEST):
            audit = p330.inspect_phase330_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p330.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p330.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 19)
            self.assertEqual(audit.compact_donors_verified, 16)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p330.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p330._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p330.inspect_phase330_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p330.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 19)
        self.assertEqual(audit.compact_donors_verified, 16)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_compact_donor_tokens_and_bt_airplane_digests(self) -> None:
        self.assertEqual(p330.EXPECTED_DONOR_BYTES["fx3_lib_airplane"], 14_488)
        self.assertEqual(p330.EXPECTED_DONOR_BYTES["fx3_lib_bt"], 158_968)
        self.assertIn(b"Always Connected", p330.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"CFexpress", p330.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"VPG200", p330.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"VPG400", p330.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"Load from Cloud", p330.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"User Menu with Lock", p330.COMPACT_DONOR_TOKENS["fx6_string_en_2"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p330._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p330.Stage70Phase330Error):
                p330._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p330.Stage70Phase330Error):
                p330._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p330.Stage70Phase330Error):
                p330._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p330.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p330._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p330.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_lib_bt"] = "0" * 64
            with unittest.mock.patch.object(
                p330, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p330.inspect_phase330_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn("digest_or_size_mismatch:fx3_lib_bt", audit.verification_notes)
        finally:
            p330._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p330.run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase330_payload_passes_clean_room(self) -> None:
        rep = p330.run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p330.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "70/70")
        self.assertTrue(rep["is_70th_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase330_payload_passes_local_donor_mode(self) -> None:
        if p330.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p330.run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p330.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 19)

    def test_13_fx3_large_windows_contain_wave60_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p330.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "BKID_MOVIE_RECORDING_MEDIA",
            "BKID_RELAY_REC",
            "PRM_HAITA_RELAY_REC_SLOT1_RO",
            "BKID_SQ_PROXY_RECORDING",
            "BKID_SQ_PROXY_FILE_FORMAT",
            "BKID_SQ_PROXY_RECORD_SETTING",
            "CAUTION_PROXY_SQ_RATE_DISABLE",
            "BKID_CLOUD_CONNECTION",
            "CLOUD_ON_FTP_OFF",
            "BKID_CNCT_WHILE_POWER_OFF",
            "BKID_ALWAYS_CONNECTED",
            "UIBIZ_BLE_POWER",
            "BT_LAUNCH_SEND_AT_POWER_OFF",
            "BKID_MYMENU_GROUP1_LIST0",
            "BKID_MYMENU_GROUP6_LIST6",
            "BKID_DISPLAY_FROM_MYMENU",
            "BKID_MYMENU_ADD_GROUP_NUM",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_large_windows_contain_wave60_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p330.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "FX6_BKID_SIMUL_REC",
            "FX6_BKID_LUT_PROXY",
            "FX6_DORMANT_BT_FUNC",
            "FX6_BKID_USER_MENU_ONLY",
            "FX6_ASSIGN_USER_MENU",
        ):
            self.assertIn(expected, labels)

    # ------------------------------------------------------------------
    # Sub-Model 70A — [Rec. Media Settings], VPG200/400 & Overflow Lock (Tests 15..32)
    # ------------------------------------------------------------------

    def test_15_dormant_prioritize_rec_media_and_sort_raw_jpeg_rejected(self) -> None:
        r1 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            prioritize_rec_media_requested=True
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p330.EOPNOTSUPP_ERRNO)
        for dormant in p330.DORMANT_PRIORITIZE_ITEMS:
            r2 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
                dormant_item_requested=dormant
            )
            self.assertFalse(r2.admitted, dormant)
            self.assertEqual(r2.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_16_movie_mode_has_3_recording_media_and_rejects_sort_recording(self) -> None:
        self.assertEqual(len(p330.STILL_RECORDING_MEDIA_MODES), 4)
        self.assertEqual(len(p330.MOVIE_RECORDING_MEDIA_MODES), 3)
        self.assertNotIn("Sort Recording", p330.MOVIE_RECORDING_MEDIA_MODES)
        for mode in (p330.SHOOT_MODE_MOVIE, p330.SHOOT_MODE_SQ):
            res = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
                shoot_mode=mode,
                recording_media_mode="Sort Recording",
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_17_still_sort_recording_shares_quality_across_slots_and_respects_slot1_vault(self) -> None:
        blocked = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_STILL,
            recording_media_mode="Sort Recording",
            tier0_vault_dual_lock_active=True,
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.errno_code, p330.EROFS_ERRNO)
        self.assertTrue(blocked.still_quality_shared_across_slots)

        ok_novault = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_STILL,
            recording_media_mode="Sort Recording",
            tier0_vault_dual_lock_active=False,
        )
        self.assertTrue(ok_novault.admitted)
        self.assertTrue(ok_novault.still_quality_shared_across_slots)

    def test_18_simult_recording_requires_identical_filesystem_parity(self) -> None:
        mismatch = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            recording_media_mode="Simult. Recording",
            slot1_filesystem="exFAT",
            slot2_filesystem="FAT32",
        )
        self.assertFalse(mismatch.admitted)
        self.assertEqual(mismatch.errno_code, p330.EINVAL_ERRNO)

        ok_parity = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            recording_media_mode="Simult. Recording",
            slot1_filesystem="exFAT",
            slot2_filesystem="exFAT",
            tier0_vault_dual_lock_active=False,
        )
        self.assertTrue(ok_parity.admitted)

    def test_19_recording_media_and_autoswitch_immune_to_camera_settings_reset(self) -> None:
        cam_rst = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            recording_media_mode="Slot 2",
            auto_switch_media="On",
            tier0_vault_dual_lock_active=False,
            nvram_autoforce_relay_off=False,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(cam_rst.admitted)
        self.assertEqual(cam_rst.effective_recording_media_mode, "Slot 2")
        self.assertEqual(cam_rst.effective_auto_switch_media, "On")

        init_rst = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            recording_media_mode="Slot 2",
            auto_switch_media="On",
            tier0_vault_dual_lock_active=False,
            nvram_autoforce_relay_off=False,
            initialize_applied=True,
        )
        self.assertEqual(init_rst.effective_recording_media_mode, "Slot 1")
        self.assertEqual(init_rst.effective_auto_switch_media, "Off")

    def test_20_critical_slot2_to_slot1_overflow_trap_duallock_erofs(self) -> None:
        trap = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            recording_media_mode="Slot 2",
            auto_switch_media="On",
            slot2_remaining_mb=0,
            tier0_vault_dual_lock_active=True,
            nvram_autoforce_relay_off=True,
            camera_settings_reset_applied=True,
        )
        self.assertFalse(trap.admitted)
        self.assertEqual(trap.errno_code, p330.EROFS_ERRNO)
        self.assertEqual(trap.effective_auto_switch_media, "Off")
        self.assertTrue(trap.overflow_dual_lock_triggered)
        self.assertEqual(trap.slot1_data_sector_writes, 0)
        self.assertFalse(trap.slot1_avf_info_mutated)

    def test_21_slot2_absent_or_error_with_autoswitch_on_blocked_on_slot1(self) -> None:
        absent = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            recording_media_mode="Slot 2",
            auto_switch_media="On",
            slot2_absent_or_error=True,
            tier0_vault_dual_lock_active=True,
            nvram_autoforce_relay_off=False,
        )
        self.assertFalse(absent.admitted)
        self.assertEqual(absent.errno_code, p330.EROFS_ERRNO)
        self.assertEqual(absent.slot1_data_sector_writes, 0)

    def test_22_slot1_direct_or_simult_blocked_by_tier0_vault_erofs(self) -> None:
        for mode in ("Slot 1", "Simult. Recording"):
            res = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
                recording_media_mode=mode,
                tier0_vault_dual_lock_active=True,
            )
            self.assertFalse(res.admitted, mode)
            self.assertEqual(res.errno_code, p330.EROFS_ERRNO)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_23_sq_1200mbps_4k_requires_cfexpress_type_a_vpg200_or_400(self) -> None:
        ok_vpg200 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="CFexpress_Type_A_VPG200",
            movie_codec="XAVC S-I 4K",
            bitrate_mbps=1200,
            fps=60,
        )
        self.assertTrue(ok_vpg200.admitted)
        self.assertEqual(ok_vpg200.vpg_gate_level, "CFexpress VPG200")

        ok_vpg400_proxy = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="CFexpress_Type_A_VPG400",
            movie_codec="XAVC S-I 4K",
            bitrate_mbps=1200,
            fps=60,
            proxy_co_recording=True,
        )
        self.assertTrue(ok_vpg400_proxy.admitted)
        self.assertEqual(ok_vpg400_proxy.vpg_gate_level, "CFexpress VPG400")
        self.assertTrue(ok_vpg400_proxy.proxy_off_advisory)

        bad_v90 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="SDXC_V90",
            movie_codec="XAVC S-I 4K",
            bitrate_mbps=1200,
            fps=60,
        )
        self.assertFalse(bad_v90.admitted)
        self.assertEqual(bad_v90.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_24_sq_hd_240fps_890mbps_requires_cfexpress_type_a(self) -> None:
        bad_v90 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="SDXC_V90",
            movie_codec="XAVC S-I HD",
            bitrate_mbps=890,
            fps=240,
        )
        self.assertFalse(bad_v90.admitted)
        self.assertEqual(bad_v90.errno_code, p330.EOPNOTSUPP_ERRNO)

        ok_cfex = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="CFexpress_Type_A_VPG200",
            movie_codec="XAVC S-I HD",
            bitrate_mbps=890,
            fps=240,
        )
        self.assertTrue(ok_cfex.admitted)

    def test_25_normal_movie_xavc_s_i_600m_accepts_v90_and_rejects_v60(self) -> None:
        ok_v90 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            slot2_card_type="SDXC_V90",
            movie_codec="XAVC S-I DCI 4K",
            bitrate_mbps=600,
            fps=60,
        )
        self.assertTrue(ok_v90.admitted)

        bad_v60 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            slot2_card_type="SDXC_V60",
            movie_codec="XAVC S-I 4K",
            bitrate_mbps=600,
            fps=60,
        )
        self.assertFalse(bad_v60.admitted)
        self.assertEqual(bad_v60.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_26_normal_movie_xavc_hs_s_4k_280m_accepts_v60_and_rejects_u3(self) -> None:
        ok_v60 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            slot2_card_type="SDXC_V60",
            movie_codec="XAVC HS 4K",
            bitrate_mbps=280,
            fps=120,
        )
        self.assertTrue(ok_v60.admitted)

        bad_u3 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            slot2_card_type="SDXC_U3_V30",
            movie_codec="XAVC S 4K",
            bitrate_mbps=280,
            fps=120,
        )
        self.assertFalse(bad_u3.admitted)
        self.assertEqual(bad_u3.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_27_cfexpress_type_b_rejected_and_sdhc_4gb_split_flagged(self) -> None:
        cfex_b = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            slot2_card_type="CFexpress_Type_B"
        )
        self.assertFalse(cfex_b.admitted)
        self.assertEqual(cfex_b.errno_code, p330.EOPNOTSUPP_ERRNO)

        sdhc = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_MOVIE,
            slot2_card_type="SDHC_32GB_U3",
            movie_codec="XAVC S HD",
            bitrate_mbps=100,
            fps=60,
        )
        self.assertTrue(sdhc.admitted)
        self.assertTrue(sdhc.sdhc_4gb_split_active)

    def test_28_sq_dci4k_requires_cfexpress_vpg200(self) -> None:
        bad_v90 = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            slot2_card_type="SDXC_V90",
            movie_codec="XAVC S-I DCI 4K",
            bitrate_mbps=600,
            fps=60,
        )
        self.assertFalse(bad_v90.admitted)
        self.assertEqual(bad_v90.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_29_fx6_simul_rec_and_independent_rec_button_set(self) -> None:
        res = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
            body_profile=p330.BODY_MODEL_FX6,
            fx6_simul_rec=True,
            fx6_body_rec_button_slot="Slot A",
            fx6_handle_rec_button_slot="Slot B",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.fx6_body_rec_button_slot, "Slot A")
        self.assertEqual(res.fx6_handle_rec_button_slot, "Slot B")

    def test_30_fx6_simul_rec_exclusions_ebusy(self) -> None:
        for excl in p330.FX6_SIMUL_REC_EXCLUSIONS:
            res = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
                body_profile=p330.BODY_MODEL_FX6,
                fx6_simul_rec=True,
                fx6_concurrent_conflict=excl,
            )
            self.assertFalse(res.admitted, excl)
            self.assertEqual(res.errno_code, p330.EBUSY_ERRNO)

    def test_31_fx6_relay_rec_exclusions_ebusy(self) -> None:
        for excl in ("Proxy Rec", "Auto Upload (Proxy): Chunk", "Wired LAN", "Streaming"):
            res = p330.simulate_rec_media_autoswitch_and_speed_gate_hil(
                body_profile=p330.BODY_MODEL_FX6,
                fx6_relay_rec=True,
                fx6_concurrent_conflict=excl,
            )
            self.assertFalse(res.admitted, excl)
            self.assertEqual(res.errno_code, p330.EBUSY_ERRNO)

    def test_32_70a_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_rec_media_autoswitch_and_speed_gate_hil(body_profile="FX9")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_rec_media_autoswitch_and_speed_gate_hil(auto_switch_media="Maybe")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_rec_media_autoswitch_and_speed_gate_hil(slot2_remaining_mb=-1)

    # ------------------------------------------------------------------
    # Sub-Model 70B — [Proxy Settings] (`sq_proxy`) & M4ROOT/SUB + Vault (Tests 33..50)
    # ------------------------------------------------------------------

    def test_33_proxy_resettable_defaults_xavc_s_hd_6m_8bit(self) -> None:
        rst = p330.simulate_proxy_settings_and_substream_hil(
            proxy_recording="On",
            proxy_file_format="XAVC HS HD",
            proxy_rec_setting="16M 4:2:0 10bit",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertEqual(rst.effective_proxy_recording, "Off")
        self.assertEqual(rst.effective_proxy_file_format, "XAVC S HD")
        self.assertEqual(rst.effective_proxy_rec_setting, "6M 4:2:0 8bit")

    def test_34_proxy_xavc_s_hd_and_hs_hd_resolution_and_bitrates(self) -> None:
        s_hd = p330.simulate_proxy_settings_and_substream_hil(
            proxy_file_format="XAVC S HD",
            proxy_rec_setting="6M 4:2:0 8bit",
        )
        self.assertTrue(s_hd.admitted)
        self.assertEqual(s_hd.proxy_resolution, "1280x720")
        self.assertEqual(s_hd.proxy_codec_family, "H.264/AVC")

        for setting in ("9M 4:2:0 10bit", "16M 4:2:0 10bit"):
            hs_hd = p330.simulate_proxy_settings_and_substream_hil(
                proxy_file_format="XAVC HS HD",
                proxy_rec_setting=setting,
            )
            self.assertTrue(hs_hd.admitted, setting)
            self.assertEqual(hs_hd.proxy_resolution, "1920x1080")
            self.assertEqual(hs_hd.proxy_codec_family, "H.265/HEVC")

    def test_35_proxy_dormant_8bit_enums_and_format_mismatch_rejected(self) -> None:
        for dormant in p330.DORMANT_PROXY_REC_SETTINGS:
            res = p330.simulate_proxy_settings_and_substream_hil(
                proxy_file_format="XAVC HS HD",
                proxy_rec_setting=dormant,
            )
            self.assertFalse(res.admitted, dormant)
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

        mismatch = p330.simulate_proxy_settings_and_substream_hil(
            proxy_file_format="XAVC S HD",
            proxy_rec_setting="9M 4:2:0 10bit",
        )
        self.assertFalse(mismatch.admitted)
        self.assertEqual(mismatch.errno_code, p330.EINVAL_ERRNO)

    def test_36_proxy_allowed_on_xavc_si_dci_4k_up_to_5994p_with_vpg_card(self) -> None:
        for fps_str in ("23.98p", "24.00p", "25p", "29.97p", "50p", "59.94p"):
            ok = p330.simulate_proxy_settings_and_substream_hil(
                shoot_mode=p330.SHOOT_MODE_MOVIE,
                main_codec="XAVC S-I DCI 4K",
                rec_frame_rate_str=fps_str,
                proxy_recording="On",
                card_speed_type="CFexpress_Type_A_VPG400",
            )
            self.assertTrue(ok.admitted, fps_str)
            self.assertEqual(ok.proxy_relpath, "/M4ROOT/SUB/C0001S03.MP4")

    def test_37_proxy_xavc_si_dci_4k_blocked_on_slow_card_by_vpg_gate(self) -> None:
        slow = p330.simulate_proxy_settings_and_substream_hil(
            main_codec="XAVC S-I DCI 4K",
            rec_frame_rate_str="59.94p",
            proxy_recording="On",
            card_media_family="SDXC",
            card_speed_type="SDXC_V60",
        )
        self.assertFalse(slow.admitted)
        self.assertEqual(slow.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_38_proxy_strict_cutoff_at_normal_movie_100p_and_11988p(self) -> None:
        for fps_str in ("100p", "119.88p"):
            res = p330.simulate_proxy_settings_and_substream_hil(
                shoot_mode=p330.SHOOT_MODE_MOVIE,
                main_codec="XAVC S 4K",
                rec_frame_rate_str=fps_str,
                proxy_recording="On",
            )
            self.assertFalse(res.admitted, fps_str)
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_39_proxy_strict_cutoff_at_sq_100fps_120fps_or_100p_11988p(self) -> None:
        r1 = p330.simulate_proxy_settings_and_substream_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            main_codec="XAVC S HD",
            rec_frame_rate_str="23.98p",
            sq_capture_fps=100,
            proxy_recording="On",
        )
        r2 = p330.simulate_proxy_settings_and_substream_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            main_codec="XAVC S HD",
            rec_frame_rate_str="23.98p",
            sq_capture_fps=120,
            proxy_recording="On",
        )
        r3 = p330.simulate_proxy_settings_and_substream_hil(
            shoot_mode=p330.SHOOT_MODE_SQ,
            main_codec="XAVC S HD",
            rec_frame_rate_str="100p",
            sq_capture_fps=60,
            proxy_recording="On",
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_40_proxy_relpath_sdxc_private_vs_cfexpress_root(self) -> None:
        sd = p330.simulate_proxy_settings_and_substream_hil(
            main_codec="XAVC S 4K",
            rec_frame_rate_str="29.97p",
            card_media_family="SDXC",
            card_speed_type="SDXC_V90",
            clip_name="C0042",
        )
        self.assertTrue(sd.admitted)
        self.assertEqual(sd.proxy_relpath, "/PRIVATE/M4ROOT/SUB/C0042S03.MP4")

        cfex = p330.simulate_proxy_settings_and_substream_hil(
            main_codec="XAVC S 4K",
            rec_frame_rate_str="29.97p",
            card_media_family="CFexpress",
            card_speed_type="CFexpress_Type_A_VPG200",
            clip_name="C0042",
        )
        self.assertTrue(cfex.admitted)
        self.assertEqual(cfex.proxy_relpath, "/M4ROOT/SUB/C0042S03.MP4")

    def test_41_proxy_non_playable_in_camera_zero_playback_frames(self) -> None:
        res = p330.simulate_proxy_settings_and_substream_hil(
            in_camera_proxy_playback_requested=True
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.on_camera_proxy_playback_frames, 0)

    def test_42_proxy_coupled_delete_protect_rejects_single_sided_edit(self) -> None:
        res = p330.simulate_proxy_settings_and_substream_hil(
            single_sided_proxy_edit_requested=True
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_43_slot1_tier0_vault_erofs_blocks_proxy_stream_and_simult_recording(self) -> None:
        for kwargs in (
            dict(target_slot=p330.SLOT_1, proxy_recording="On"),
            dict(target_slot=p330.SLOT_2, recording_media_mode="Simult. Recording", proxy_recording="On"),
        ):
            res = p330.simulate_proxy_settings_and_substream_hil(**kwargs)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p330.EROFS_ERRNO)
            self.assertTrue(res.tier0_vault_firewall_triggered)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_44_slot1_tier0_vault_erofs_blocks_coupled_delete_and_protect(self) -> None:
        for action in ("Delete", "Protect"):
            res = p330.simulate_proxy_settings_and_substream_hil(
                target_slot=p330.SLOT_1,
                proxy_recording="Off",
                coupled_delete_or_protect_action=action,
            )
            self.assertFalse(res.admitted, action)
            self.assertEqual(res.errno_code, p330.EROFS_ERRNO)
            self.assertTrue(res.tier0_vault_firewall_triggered)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_45_send_to_smartphone_proxy_filter_modes(self) -> None:
        for flt in p330.VALID_SEND_TARGET_FILTERS:
            res = p330.simulate_proxy_settings_and_substream_hil(send_target_filter=flt)
            self.assertTrue(res.admitted, flt)
            self.assertEqual(res.send_target_filter, flt)

    def test_46_fx6_xavc_proxy_1920x1080_9mbps_avc_and_chunk_durations(self) -> None:
        for dur in p330.FX6_PROXY_CHUNK_DURATIONS:
            res = p330.simulate_proxy_settings_and_substream_hil(
                body_profile=p330.BODY_MODEL_FX6,
                fx6_chunk_duration=dur,
            )
            self.assertTrue(res.admitted, dur)
            self.assertEqual(res.proxy_resolution, "1920x1080")
            self.assertEqual(res.proxy_rec_setting, "1920x1080 9Mbps AVC")
            self.assertEqual(res.fx6_chunk_slot, "Slot B")

    def test_47_fx6_proxy_and_chunk_exclusions_ebusy(self) -> None:
        for excl in ("Simul Rec", "S&Q Motion", "Interval Rec"):
            res = p330.simulate_proxy_settings_and_substream_hil(
                body_profile=p330.BODY_MODEL_FX6,
                fx6_chunk_duration="30s",
                fx6_concurrent_conflict=excl,
            )
            self.assertFalse(res.admitted, excl)
            self.assertEqual(res.errno_code, p330.EBUSY_ERRNO)

        relay_chunk = p330.simulate_proxy_settings_and_substream_hil(
            body_profile=p330.BODY_MODEL_FX6,
            fx6_chunk_duration="2min",
            fx6_concurrent_conflict="Relay Rec",
        )
        self.assertFalse(relay_chunk.admitted)
        self.assertEqual(relay_chunk.errno_code, p330.EBUSY_ERRNO)

    def test_48_slot2_coupled_delete_protect_when_proxy_off_and_not_simult(self) -> None:
        res = p330.simulate_proxy_settings_and_substream_hil(
            target_slot=p330.SLOT_2,
            recording_media_mode="Slot 2",
            proxy_recording="Off",
            coupled_delete_or_protect_action="Protect",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.tier0_vault_firewall_triggered)

    def test_49_proxy_disabled_allows_11988p_when_proxy_off(self) -> None:
        res = p330.simulate_proxy_settings_and_substream_hil(
            main_codec="XAVC S 4K",
            rec_frame_rate_str="119.88p",
            proxy_recording="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_proxy_recording, "Off")

    def test_50_70b_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_proxy_settings_and_substream_hil(proxy_file_format="ProRes")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_proxy_settings_and_substream_hil(target_slot=3)
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_proxy_settings_and_substream_hil(fx6_chunk_duration="5min")

    # ------------------------------------------------------------------
    # Sub-Model 70C — [Creators' Cloud], [C3 Portal] & Power-OFF BLE Zero-RF (Tests 51..68)
    # ------------------------------------------------------------------

    def test_51_cloud_connection_and_information_survive_camera_settings_reset(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cloud_connection="On",
            cloud_account_bound=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_cloud_connection, "On")
        self.assertTrue(res.cloud_credentials_retained)

    def test_52_cloud_connection_and_information_star_survive_initialize(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cloud_connection="On",
            cloud_account_bound=True,
            initialize_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_cloud_connection, "On")
        self.assertTrue(res.cloud_credentials_retained)
        self.assertEqual(res.rf_packets_transmitted, 0)

    def test_53_cloud_cleared_only_by_manual_account_delete(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cloud_connection="On",
            cloud_account_bound=True,
            manual_cloud_account_delete_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_cloud_connection, "Off")
        self.assertFalse(res.cloud_credentials_retained)

    def test_54_creators_cloud_requires_ver500_or_later(self) -> None:
        for old_fw in (p330.FW_VER_200, p330.FW_VER_300, p330.FW_VER_400):
            res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
                firmware_version=old_fw,
                cloud_connection="On",
            )
            self.assertFalse(res.admitted, old_fw)
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

        v500 = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            firmware_version=p330.FW_VER_500,
            cloud_connection="On",
        )
        self.assertTrue(v500.admitted)

    def test_55_ver700_clip_flag_filter_vs_pre700_off(self) -> None:
        for flag in ("OK", "NG", "KEEP"):
            v702 = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
                firmware_version=p330.FW_VER_702,
                clip_flag_filter=flag,
            )
            self.assertTrue(v702.admitted, flag)
            self.assertEqual(v702.clip_flag_filter, flag)

        v600 = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            firmware_version=p330.FW_VER_600,
            clip_flag_filter="OK",
        )
        self.assertTrue(v600.admitted)
        self.assertEqual(v600.clip_flag_filter, "Off")

    def test_56_cloud_connection_and_ftp_mutually_exclusive_ebusy(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cloud_connection="On",
            ftp_transfer_enabled=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p330.EBUSY_ERRNO)

    def test_57_c3_portal_private_and_share_modes(self) -> None:
        for mode in p330.VALID_C3_PORTAL_MODES:
            res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(c3_portal_mode=mode)
            self.assertTrue(res.admitted, mode)
            self.assertEqual(res.c3_portal_mode, mode)

    def test_58_cnct_while_power_off_survives_cam_reset_and_clears_on_net_reset_or_init(self) -> None:
        cam_rst = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cnct_while_power_off="On",
            zero_rf_bench_mode=False,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(cam_rst.admitted)
        self.assertEqual(cam_rst.effective_cnct_while_power_off, "On")

        net_rst = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cnct_while_power_off="On",
            bluetooth_function="On",
            airplane_mode="On",
            reset_network_set_applied=True,
        )
        self.assertTrue(net_rst.admitted)
        self.assertEqual(net_rst.effective_cnct_while_power_off, "Off")
        self.assertEqual(net_rst.effective_bluetooth_function, "Off")

        init_rst = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cnct_while_power_off="On",
            bluetooth_function="On",
            airplane_mode="On",
            initialize_applied=True,
        )
        self.assertTrue(init_rst.admitted)
        self.assertEqual(init_rst.effective_cnct_while_power_off, "Off")
        self.assertEqual(init_rst.effective_bluetooth_function, "Off")

    def test_59_critical_power_off_ble_trap_rejects_switch_off_assumption(self) -> None:
        trap = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cnct_while_power_off="On",
            bluetooth_function="On",
            bluetooth_paired=True,
            airplane_mode="Off",
            physical_power_switch="OFF",
            zero_rf_bench_mode=True,
            assume_power_off_is_zero_rf_requested=True,
        )
        self.assertFalse(trap.admitted)
        self.assertEqual(trap.errno_code, p330.EPERM_ERRNO)
        self.assertTrue(trap.ble_standby_powered)
        self.assertTrue(trap.ble_power_off_trap_detected)
        self.assertEqual(trap.rf_packets_transmitted, 0)

    def test_60_zero_rf_3lock_requires_airplane_on_cnct_off_bt_off(self) -> None:
        # Missing any one of the 3 locks fails closed in zero_rf_bench_mode
        for bad_kwargs in (
            dict(airplane_mode="Off", cnct_while_power_off="Off", bluetooth_function="Off"),
            dict(airplane_mode="On", cnct_while_power_off="On", bluetooth_function="Off"),
            dict(airplane_mode="On", cnct_while_power_off="Off", bluetooth_function="On"),
        ):
            res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
                zero_rf_bench_mode=True,
                **bad_kwargs,
            )
            self.assertFalse(res.admitted, str(bad_kwargs))
            self.assertEqual(res.errno_code, p330.EPERM_ERRNO)

        ok = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            airplane_mode="On",
            cnct_while_power_off="Off",
            bluetooth_function="Off",
            zero_rf_bench_mode=True,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.ble_standby_powered)
        self.assertEqual(ok.rf_packets_transmitted, 0)

    def test_61_fx6_has_zero_bluetooth_and_rejects_ble_wake(self) -> None:
        for bad in (
            dict(cnct_while_power_off="On"),
            dict(bluetooth_function="On"),
        ):
            res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
                body_profile=p330.BODY_MODEL_FX6,
                **bad,
            )
            self.assertFalse(res.admitted, str(bad))
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_62_fx6_admits_c3_portal_over_lan_wifi_with_zero_bluetooth(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            body_profile=p330.BODY_MODEL_FX6,
            c3_portal_mode="Cloud(Share)",
            cloud_connection="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_bluetooth_function, "Off")
        self.assertEqual(res.effective_cnct_while_power_off, "Off")

    def test_63_power_switch_on_without_zero_rf_bench_mode(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            physical_power_switch="ON",
            airplane_mode="On",
            cnct_while_power_off="Off",
            bluetooth_function="Off",
            zero_rf_bench_mode=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.rf_packets_transmitted, 0)

    def test_64_ble_standby_powered_flagged_even_if_bt_off_when_paired_and_poweroff_on(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            physical_power_switch="OFF",
            airplane_mode="Off",
            cnct_while_power_off="On",
            bluetooth_function="Off",
            bluetooth_paired=True,
            zero_rf_bench_mode=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p330.EPERM_ERRNO)
        self.assertTrue(res.ble_standby_powered)

    def test_65_rf_nvs_mutation_bytes_always_zero(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            airplane_mode="On",
            cnct_while_power_off="Off",
            bluetooth_function="Off",
        )
        self.assertEqual(res.rf_nvs_mutation_bytes, 0)

    def test_66_fx3_cloud_info_survives_network_reset_too(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            cloud_connection="On",
            cloud_account_bound=True,
            airplane_mode="On",
            reset_network_set_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.cloud_credentials_retained)
        self.assertEqual(res.effective_cloud_connection, "On")

    def test_67_fx6_clip_flag_off(self) -> None:
        res = p330.simulate_cloud_c3portal_and_poweroff_ble_hil(
            body_profile=p330.BODY_MODEL_FX6,
            clip_flag_filter="OK",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.clip_flag_filter, "Off")

    def test_68_70c_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_cloud_c3portal_and_poweroff_ble_hil(c3_portal_mode="Public")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_cloud_c3portal_and_poweroff_ble_hil(clip_flag_filter="BAD")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_cloud_c3portal_and_poweroff_ble_hil(physical_power_switch="SLEEP")

    # ------------------------------------------------------------------
    # Sub-Model 70D — [My Menu] 6x7=42 Slots vs FX6 20-Item User Menu + Lock (Tests 69..84)
    # ------------------------------------------------------------------

    def test_69_fx3_mymenu_exact_6_pages_x_7_items_42_slots(self) -> None:
        self.assertEqual(p330.MYMENU_PAGES, 6)
        self.assertEqual(p330.MYMENU_ITEMS_PER_PAGE, 7)
        self.assertEqual(p330.MYMENU_EXACT_SLOT_CAPACITY, 42)
        for g in range(1, 7):
            for idx in (0, 6):
                res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
                    group_number=g,
                    item_index=idx,
                    item_count_requested=42,
                )
                self.assertTrue(res.admitted, (g, idx))
                self.assertEqual(res.nvram_key, f"BKID_APP_mymenu_group{g}_setting_list{idx}")
                self.assertEqual(res.max_capacity, 42)

    def test_70_fx3_mymenu_rejects_group0_group7_list7_and_gt42_einval(self) -> None:
        for bad_kwargs in (
            dict(group_number=0, item_index=0),
            dict(group_number=7, item_index=0),
            dict(group_number=1, item_index=7),
            dict(group_number=1, item_index=-1),
            dict(group_number=1, item_index=0, item_count_requested=43),
        ):
            res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(**bad_kwargs)
            self.assertFalse(res.admitted, str(bad_kwargs))
            self.assertEqual(res.errno_code, p330.EINVAL_ERRNO)

    def test_71_fx3_mymenu_rejects_playback_items_eopnotsupp(self) -> None:
        res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            operation="Add Item",
            item_domain="Playback",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_72_fx3_mymenu_all_6_operations_supported(self) -> None:
        self.assertEqual(len(p330.FX3_MYMENU_ALLOWED_OPS), 6)
        for op in p330.FX3_MYMENU_ALLOWED_OPS:
            res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(operation=op)
            self.assertTrue(res.admitted, op)

    def test_73_fx3_mymenu_survives_camera_settings_reset(self) -> None:
        res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            item_count_requested=42,
            display_from_my_menu="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_item_count, 42)
        self.assertEqual(res.effective_display_from_my_menu, "On")

    def test_74_fx3_mymenu_cleared_by_delete_all_or_initialize(self) -> None:
        del_all = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            item_count_requested=42,
            display_from_my_menu="On",
            delete_all_applied=True,
        )
        self.assertTrue(del_all.admitted)
        self.assertEqual(del_all.effective_item_count, 0)
        self.assertEqual(del_all.effective_display_from_my_menu, "On")

        init = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            item_count_requested=42,
            display_from_my_menu="On",
            initialize_applied=True,
        )
        self.assertTrue(init.admitted)
        self.assertEqual(init.effective_item_count, 0)
        self.assertEqual(init.effective_display_from_my_menu, "Off")

    def test_75_fx6_user_menu_20_item_capacity_and_21_rejected(self) -> None:
        ok = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=20,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.max_capacity, 20)
        self.assertEqual(ok.effective_item_count, 20)

        bad = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=21,
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p330.EINVAL_ERRNO)

    def test_76_fx6_user_menu_only_exported_in_all_file_not_scene_file(self) -> None:
        res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=15,
            fx6_user_menu_mode="User Menu Only",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.fx6_locked)
        self.assertTrue(res.exported_in_all_file)
        self.assertFalse(res.exported_in_scene_file)

    def test_77_fx6_user_menu_with_lock_requires_combo_hold(self) -> None:
        hidden = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=10,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=False,
            fx6_pin_code="0000",
        )
        self.assertFalse(hidden.admitted)
        self.assertEqual(hidden.errno_code, p330.EOPNOTSUPP_ERRNO)
        self.assertTrue(hidden.fx6_locked)

    def test_78_fx6_user_menu_with_lock_pin_unlock_and_wrong_pin_eacces(self) -> None:
        ok = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=10,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=True,
            fx6_pin_code="4270",
            fx6_unlock_attempt_pin="4270",
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.fx6_locked)
        self.assertFalse(ok.exported_in_all_file)
        self.assertFalse(ok.exported_in_scene_file)

        bad = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=10,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=True,
            fx6_pin_code="4270",
            fx6_unlock_attempt_pin="9999",
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p330.EACCES_ERRNO)
        self.assertTrue(bad.fx6_locked)

    def test_79_fx6_user_menu_with_lock_invalid_pin_format_einval(self) -> None:
        for bad_pin in ("123", "12345", "ABCD"):
            res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
                body_profile=p330.BODY_MODEL_FX6,
                item_count_requested=10,
                fx6_user_menu_mode="User Menu with Lock",
                fx6_combo_hold_revealed=True,
                fx6_pin_code=bad_pin,
            )
            self.assertFalse(res.admitted, bad_pin)
            self.assertEqual(res.errno_code, p330.EINVAL_ERRNO)

    def test_80_fx6_user_menu_with_lock_pin_excluded_from_all_file_and_scene_file(self) -> None:
        locked = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            body_profile=p330.BODY_MODEL_FX6,
            item_count_requested=20,
            fx6_user_menu_mode="User Menu with Lock",
            fx6_combo_hold_revealed=True,
            fx6_pin_code="0000",
        )
        self.assertTrue(locked.admitted)
        self.assertTrue(locked.fx6_locked)
        self.assertFalse(locked.exported_in_all_file)
        self.assertFalse(locked.exported_in_scene_file)

    def test_81_fx3_rejects_fx6_rental_house_lock_modes(self) -> None:
        for lock_mode in ("User Menu Only", "User Menu with Lock"):
            res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
                body_profile=p330.BODY_MODEL_FX3,
                fx6_user_menu_mode=lock_mode,
            )
            self.assertFalse(res.admitted, lock_mode)
            self.assertEqual(res.errno_code, p330.EOPNOTSUPP_ERRNO)

    def test_82_fx3_mymenu_display_from_my_menu_off_default_vs_on(self) -> None:
        off_res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
            display_from_my_menu="Off"
        )
        self.assertTrue(off_res.admitted)
        self.assertEqual(off_res.effective_display_from_my_menu, "Off")

    def test_83_fx3_mymenu_allows_non_playback_domains(self) -> None:
        for domain in ("Shooting", "Exposure/Color", "Focus", "Setup", "Network"):
            res = p330.simulate_mymenu_and_fx6_user_menu_lock_hil(
                operation="Add Item",
                item_domain=domain,
            )
            self.assertTrue(res.admitted, domain)

    def test_84_70d_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_mymenu_and_fx6_user_menu_lock_hil(operation="Clone Page")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_mymenu_and_fx6_user_menu_lock_hil(item_domain="Secret")
        with self.assertRaises(p330.Stage70Phase330Error):
            p330.simulate_mymenu_and_fx6_user_menu_lock_hil(fx6_user_menu_mode="Guest Menu")

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 70 Wiring (Tests 85..96)
    # ------------------------------------------------------------------

    def test_85_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_rec_media_autoswitch_proxy_cloud_mymenu_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("70/70", proc.stdout)

    def test_86_suite_cli_help_percent_escaping_and_stage70_flags(self) -> None:
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
        self.assertIn("70/70 Milestone", proc.stdout)
        self.assertIn("--include-stage70", proc.stdout)
        self.assertIn("--skip-stage70", proc.stdout)
        self.assertIn("--no-include-stage70", proc.stdout)
        self.assertIn("--skip-phase330", proc.stdout)

    def test_87_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p330.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 330 Stage 70 (70/70 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p330.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "70/70")
        self.assertTrue(parsed["is_70th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_88_no_hardcoded_usr_bin_python3_in_stage70_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_rec_media_autoswitch_proxy_cloud_mymenu_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_89_suite_default_config_enables_stage70_and_full_run_contains_70_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase330_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil)
        self.assertTrue(cfg.include_stage70)
        self.assertTrue(cfg.stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil)

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 70)
        s70 = rep["stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil"]
        self.assertTrue(s70["all_checks_passed"])
        self.assertTrue(s70["is_70th_stage_milestone"])
        self.assertEqual(s70["milestone"], "70/70")
        self.assertEqual(s70["phase_number"], 330)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_90_suite_skip_flags_and_summary_cli_for_stage70(self) -> None:
        for flag in ("--skip-stage70", "--no-include-stage70", "--skip-phase330"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage70"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage70", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil=CLEAN_ROOM_SYNTHETIC("
            "m70=70/70,ovf_byp=0,px_pb=0,ble_rf=0,mm_cap=42,rf_tx=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_91_suite_tamper_70a_prioritize_or_overflow_bypass_detected(self) -> None:
        for attr, val in (
            ("PRIORITIZE_REC_MEDIA_EXPOSED_EVENTS", 1),
            ("MOVIE_SORT_RECORDING_EXPOSED_EVENTS", 1),
            ("SIMULT_FS_MISMATCH_BYPASS_EVENTS", 1),
            ("SLOT2_TO_SLOT1_OVERFLOW_BYPASS_EVENTS", 1),
            ("SDXC_1200M_OR_CFEX_B_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p330, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_70b_proxy_cutoff_playback_or_slot1_detected(self) -> None:
        for attr, val in (
            ("PROXY_HIGHFPS_100P_120FPS_BYPASS_EVENTS", 1),
            ("ON_CAMERA_PROXY_PLAYBACK_FRAMES", 1),
            ("PROXY_COUPLED_DELETE_SPLIT_EVENTS", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("SLOT1_VAULT_PROXY_MUTATION_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p330, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_suite_tamper_70c_ble_zerorf_or_fx6_bt_detected(self) -> None:
        for attr, val in (
            ("POWER_OFF_BLE_ZERO_RF_VIOLATIONS", 1),
            ("FX6_BLUETOOTH_HARDWARE_PRESENT", True),
            ("FX6_BLUETOOTH_POWEROFF_WAKE_EXPOSED_EVENTS", 1),
            ("RF_PACKETS_TRANSMITTED", 1),
            ("RF_NVS_MUTATION_BYTES", 16),
        ):
            with unittest.mock.patch.object(p330, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_94_suite_tamper_70d_mymenu_42_or_fx6_pin_leak_detected(self) -> None:
        for attr, val in (
            ("MYMENU_EXACT_SLOT_CAPACITY", 36),
            ("FX6_USER_MENU_CAPACITY", 42),
            ("MYMENU_OUT_OF_BOUNDS_OR_PLAYBACK_EVENTS", 1),
            ("FX6_USER_MENU_LOCK_PIN_FILE_LEAK_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p330, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_95_suite_tamper_hard_write_redlines_detected(self) -> None:
        for attr, val in (
            ("PERSISTENT_EMMC_WRITES_AUTHORIZED", True),
            ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True),
            ("PHYSICAL_DEVICE_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
        ):
            with unittest.mock.patch.object(p330, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_96_stage70_all_redline_zero_keys_verified(self) -> None:
        rep = p330.run_phase330_rec_media_autoswitch_proxy_cloud_mymenu_coemulation(
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
            "prioritize_rec_media_exposed_events",
            "movie_sort_recording_exposed_events",
            "simult_fs_mismatch_bypass_events",
            "slot2_to_slot1_overflow_bypass_events",
            "sdxc_1200m_or_cfex_b_bypass_events",
            "proxy_highfps_100p_120fps_bypass_events",
            "on_camera_proxy_playback_frames",
            "proxy_coupled_delete_split_events",
            "slot1_data_sector_writes",
            "slot1_vault_proxy_mutation_events",
            "power_off_ble_zero_rf_violations",
            "fx6_bluetooth_poweroff_wake_exposed_events",
            "mymenu_out_of_bounds_or_playback_events",
            "fx6_user_menu_lock_pin_file_leak_events",
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
