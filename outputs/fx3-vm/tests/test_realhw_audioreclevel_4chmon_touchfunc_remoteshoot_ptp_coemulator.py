#!/usr/bin/env python3
"""Unit tests for Phase 365 (Stage 82 — 82/82 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-72:
- 82A: `[Audio Rec Level]` (`0..31` = `32` steps, default `26`
  `adj_audio_rec_level_defult`, `Delete` key reset, `[Camera Settings Reset]`
  resettable), internal stereo mic & body `3.5mm MIC` scope, permanent
  always-on non-defeatable body limiter (`EOPNOTSUPP=95`), `XLR-H1`
  `HANDLE AUDIO = ON` physical switch bypass (`greyed_out=True`,
  `LINE +4 dBu`, `MIC`/`MIC+48V ATT 0/10/20 dB` = `-60/-50/-40 dBu`,
  `AUTO/MAN(/LINK)` disabling dial 2, `48kHz/24bit` `2ch`/`4ch`),
  `3.5mm MIC > XLR-H1 > Internal Mic` preemption, `S&Q` `0ch` lock
  (`EBUSY=16`), vs FX6 `Audio -> [Audio Input]` (`CH1..CH4 Input Select`,
  `0..99`, 3-tier Reference, exact 6-step `Limiter Mode`, `SG 1kHz`),
- 82B: `[Audio Out Timing]` (`Live` default / `Lip Sync`, `Can be reset`,
  `S&Q` disabled `EBUSY=16`), `Setup -> [Sound Option]` `[Volume Settings]`
  (`0..15` default `7`, Reset-resistant `Not available`, speaker howl risk
  guard) & `[4ch Audio Monitoring]` exact 5 options (`CH1/CH2` default,
  `CH3/CH4`, `CH1+3/CH2+4`, `CH1/CH1`, `CH2/CH2` — rejecting errata strings
  `EOPNOTSUPP=95`, Reset-resistant `Not available`, independent of HDMI
  `[4ch Audio Output]`) vs FX6 7-option `Monitor CH`, `Headphone Out`,
  `Volume 0..50`, `SDI 4ch`, zero physical `"MONITOR VOL +/-"` button
  (`ENODEV=19`),
- 82C: `Setup -> [Touch Operation]` exact 4 Reset-resistant (`Not available`)
  items (`[Touch Operation]`, `[Touch Sensitivity]`, `[Touch Func. in
  Shooting]` shared across Still/Movie/`S&Q`, `[Swipe Up]`), 100% dormant
  `[Touch Panel/Pad]`, `[Touch Shutter]`, and `[Touch AE]` (`EOPNOTSUPP=95`),
  `[Spot Metering Point] = Focus Point Link` static-only (never follows
  moving tracking box -> `EOPNOTSUPP=95`) vs FX6 `Touch Operation`, `Touch
  Function in MF` (`Spot Focus` disabled on manual lens / `De-Squeeze` /
  `Focus Magnifier` -> `EBUSY=16`), Ver. 6.00+ `BIG6` & full menu touch,
- 82D: `[PC Remote Function]` (`Ver. 1.01`) -> `[Remote Shoot Setting]`
  (`Ver. 2.00..7.02`, Reset-resistant vs `[Camera Settings Reset]`, cleared by
  `[Reset Network Set.]` / `[Initialize]`), factory default `Dest.+Camera`,
  `CONNECTED` save-dest lock (`EBUSY=16`), USB `/dev/usb/sicd_*` (`054c:0d2b`)
  & PTP-IP TCP `15740`, `Destination Only` cardless RAM capture (`slot1 == 0`,
  `rf_tx_packets == 0`) vs `Dest.+Camera` & `Camera Only` cardless
  (`ENODEV=19`) and Tier-0 `Slot 1` (`EROFS=30`) vs FX6 `Camera Remote
  Control` & zero `Still Img. Save Dest.` UI (`EOPNOTSUPP=95`)
HIL (100 four-mode tests).
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
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulator as p365  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..81 for Stage 82 isolation tests."""
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
]


class TestPhase365Wave72Stage82CoEmulator(unittest.TestCase):
    # =========================================================================
    # Tests 01..16: Schema, Redlines, 25-Donor O_RDONLY & 4-Mode Clean-Room
    # =========================================================================

    def test_01_schema_milestone_and_version_constants(self) -> None:
        self.assertEqual(
            p365.SCHEMA_ID,
            "phase365_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation_v1",
        )
        self.assertEqual(p365.PHASE_NUMBER, 365)
        self.assertEqual(p365.STAGE_INDEX, 82)
        self.assertEqual(p365.STAGE_TOTAL, 82)
        self.assertEqual(p365.MILESTONE_LABEL, "82/82")
        self.assertTrue(p365.IS_82ND_STAGE_MILESTONE)
        self.assertEqual(p365.PHASE_365_VERSION, "365.0.0")

    def test_02_tier0_redline_constants_hard_locked(self) -> None:
        self.assertFalse(p365.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertTrue(p365.P8_CP_MUTATION_FORBIDDEN)
        self.assertEqual(p365.NOP_COUNT, 0)
        self.assertEqual(p365.CP_MUTATION_BYTES, 0)
        self.assertEqual(p365.WBI_MUTATION_BYTES, 0)
        self.assertEqual(p365.CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(p365.CNFLASHA_MUTATION_BYTES, 0)
        self.assertTrue(p365.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p365.NVRAM_PERSISTENT_WRITES, 0)
        self.assertEqual(p365.BK4_PERSISTENT_NVRAM_WRITES, 0)
        self.assertEqual(p365.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p365.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p365.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p365.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p365.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertEqual(p365.SLOT1_SECTOR_WRITES, 0)
        self.assertEqual(p365.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertFalse(p365.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p365.RF_TX_PACKETS, 0)
        self.assertEqual(p365.RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(p365.RF_NVS_MUTATION_BYTES, 0)
        self.assertEqual(p365.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_wave72_submodel_invariant_constants(self) -> None:
        self.assertEqual(p365.FX3_AUDIO_REC_LEVEL_MIN, 0)
        self.assertEqual(p365.FX3_AUDIO_REC_LEVEL_MAX, 31)
        self.assertEqual(p365.FX3_AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertEqual(p365.FX3_AUDIO_REC_LEVEL_STEPS_COUNT, 32)
        self.assertTrue(p365.FX3_BODY_LIMITER_ALWAYS_ON)
        self.assertEqual(p365.FX6_LIMITER_MODE_STEPS_COUNT, 6)
        self.assertTrue(p365.FX6_4STEP_LIMITER_RUMOR_DISPROVED)
        self.assertEqual(p365.FX3_4CH_MONITORING_OPTIONS_COUNT, 5)
        self.assertTrue(p365.FX3_3OPTION_ERRATA_CORRECTED)
        self.assertEqual(p365.FX6_MONITOR_CH_OPTIONS_COUNT, 7)
        self.assertFalse(p365.FX6_PHYSICAL_MONITOR_VOL_BUTTON_PRESENT)
        self.assertEqual(p365.FX3_TOUCH_SETUP_ACTIVE_ITEMS_COUNT, 4)
        self.assertEqual(p365.FX3_PTP_USB_VID_PID, "054c:0d2b")
        self.assertEqual(p365.FX3_PTPIP_TCP_PORT, 15740)
        self.assertEqual(p365.FX3_REMOTE_SHOOT_FACTORY_DEFAULT_DEST, "Dest.+Camera")

    def test_04_donor_spec_count_20_compact_plus_5_window_equals_25(self) -> None:
        self.assertEqual(len(p365.PHASE365_COMPACT_DONORS), 20)
        self.assertEqual(len(p365.PHASE365_WINDOW_DONORS), 5)
        self.assertEqual(
            len(p365.PHASE365_COMPACT_DONORS) + len(p365.PHASE365_WINDOW_DONORS), 25
        )
        for spec in p365.PHASE365_COMPACT_DONORS:
            self.assertLessEqual(spec.expected_size, p365._COMPACT_MAX_READ_BYTES)
        for wspec in p365.PHASE365_WINDOW_DONORS:
            for off, _lbl, _needle in wspec.windows:
                self.assertGreaterEqual(off, 0)
                self.assertEqual(off % 2048, 0)
            for off, _lbl, _forb in wspec.absent_windows:
                self.assertGreaterEqual(off, 0)
                self.assertEqual(off % 2048, 0)

    def test_05_mocked_donorless_work_root_none_clean_room(self) -> None:
        audit = p365.inspect_phase365_wave72_donors(work_root=None)
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertFalse(audit["work_root_available"])
        self.assertEqual(audit["total_donors_count"], 25)
        self.assertTrue(audit["all_donors_verified"])
        self.assertEqual(audit["raw_firmware_bytes_leaked"], 0)
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_06_nonexistent_work_root_fallback_clean_room(self) -> None:
        audit = p365.inspect_phase365_wave72_donors(
            work_root="/nonexistent/path/for/phase365_stage82_test"
        )
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit["all_donors_verified"])
        self.assertEqual(audit["total_donors_count"], 25)

    def test_07_env_fx3_clean_room_test_1_mode(self) -> None:
        audit = p365.inspect_phase365_wave72_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit["forced_clean_room"])
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_08_env_force_clean_room_1_mode(self) -> None:
        audit = p365.inspect_phase365_wave72_donors(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit["forced_clean_room"])
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_09_donor_disabled_sentinel_mode(self) -> None:
        audit = p365.inspect_phase365_wave72_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p365._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(audit["forced_clean_room"])
        self.assertIsNone(
            p365.resolve_mac_work_root(work_root=p365._DONOR_DISABLED_SENTINEL)
        )
        self.assertIsNone(p365.resolve_mac_work_root(work_root="   "))

    def test_10_normal_mode_or_ci_auto_dispatch(self) -> None:
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["milestone"], "82/82")
        if IS_CI or p365.is_forced_clean_room():
            self.assertIn(
                rep["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
            )
        else:
            root = p365.resolve_mac_work_root()
            if root is not None and root.exists():
                self.assertEqual(rep["source_mode"], "LOCAL_DONOR_O_RDONLY")
            else:
                self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_11_bounded_window_exceeding_4096_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "dummy.bin"
            f.write_bytes(b"A" * 8192)
            with self.assertRaises(p365.Stage82Phase365Error):
                p365._read_bounded_window_o_rdonly(f, 0, 4097)

    def test_12_compact_exceeding_1mib_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "big.bin"
            f.write_bytes(b"\x00" * (p365._COMPACT_MAX_READ_BYTES + 1))
            with self.assertRaises(p365.Stage82Phase365Error):
                p365._read_full_compact_o_rdonly(f)

    def test_13_os_open_always_uses_o_rdonly_never_write_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "ro_probe.bin"
            f.write_bytes(b"SonyFX3Wave72Test" + b"\x00" * 4096)
            opened_flags: list[int] = []
            real_open = os.open

            def spy_open(path: str, flags: int, *args: object) -> int:
                opened_flags.append(flags)
                return real_open(path, flags, *args)

            with unittest.mock.patch("os.open", side_effect=spy_open):
                _ = p365._read_full_compact_o_rdonly(f)
                _ = p365._read_bounded_window_o_rdonly(f, 0, 4096)

            self.assertEqual(len(opened_flags), 2)
            for fl in opened_flags:
                self.assertEqual(fl, os.O_RDONLY)

    def test_14_tampered_compact_donor_size_and_sha_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for s in p365.PHASE365_COMPACT_DONORS:
                p = root / s.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"X" * s.expected_size)
            for w in p365.PHASE365_WINDOW_DONORS:
                p = root / w.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"Y" * 4096)
            # Corrupt first compact donor's sha256 -> raises Stage82Phase365Error
            with self.assertRaises(p365.Stage82Phase365Error):
                p365.inspect_phase365_wave72_donors(work_root=root, force_clean_room=False)

    def test_15_tampered_compact_forbidden_token_rejected(self) -> None:
        payload_bytes = b"Audio Rec Level CH1/CH2 CH1+2/CH3+4"
        sha = __import__("hashlib").sha256(payload_bytes).hexdigest()
        fake_spec = p365.CompactDonorSpec(
            name="fake_en_f",
            rel_path="sub/en_f.uxc",
            expected_size=len(payload_bytes),
            expected_sha256=sha,
            required_tokens=(b"Audio Rec Level", b"CH1/CH2"),
            absent_tokens=(b"CH1+2/CH3+4",),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / fake_spec.rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(payload_bytes)
            with (
                unittest.mock.patch.object(p365, "PHASE365_COMPACT_DONORS", (fake_spec,)),
                unittest.mock.patch.object(p365, "PHASE365_WINDOW_DONORS", ()),
            ):
                with self.assertRaises(p365.Stage82Phase365Error):
                    p365.inspect_phase365_wave72_donors(
                        work_root=root, force_clean_room=False
                    )

    def test_16_tampered_window_forbidden_token_rejected(self) -> None:
        buf = b"MONITOR VOL" + b"\x00" * (4096 - len(b"MONITOR VOL"))
        h4k = __import__("hashlib").sha256(buf).hexdigest()
        fake_w = p365.WindowDonorSpec(
            name="fake_fx6",
            rel_path="sub/appFw.so",
            expected_size=len(buf),
            head4k_sha256=h4k,
            windows=(),
            absent_windows=((0, "NO_MONITOR_VOL", b"MONITOR VOL"),),
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / fake_w.rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(buf)
            with (
                unittest.mock.patch.object(p365, "PHASE365_COMPACT_DONORS", ()),
                unittest.mock.patch.object(p365, "PHASE365_WINDOW_DONORS", (fake_w,)),
            ):
                with self.assertRaises(p365.Stage82Phase365Error):
                    p365.inspect_phase365_wave72_donors(
                        work_root=root, force_clean_room=False
                    )

    # =========================================================================
    # Tests 17..36: Sub-Model 82A — [Audio Rec Level] / XLR-H1 Bypass / Limiter
    #               vs FX6 3-Tier Reference & Exact 6-Step Limiter Mode
    # =========================================================================

    def test_17_82a_fx3_audio_rec_level_default_26_and_menu_path(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.menu_path, "Shooting -> [Audio Recording] -> [Audio Rec Level]")
        self.assertEqual(r.body_audio_rec_level, 26)
        self.assertEqual(r.active_input_source, "internal_stereo_mic")
        self.assertFalse(r.body_audio_rec_level_greyed_out)
        self.assertTrue(r.body_limiter_always_on)
        self.assertFalse(r.limiter_defeatable)
        self.assertTrue(r.resettable_via_camera_settings_reset)

    def test_18_82a_fx3_audio_rec_level_bounds_0_and_31_admitted(self) -> None:
        for val in (0, 1, 26, 31):
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_rec_level=val
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.body_audio_rec_level, val)

    def test_19_82a_fx3_audio_rec_level_out_of_range_einval(self) -> None:
        for bad in (-1, 32, 99):
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_rec_level=bad
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_20_82a_fx3_delete_key_and_camera_settings_reset_restore_26(self) -> None:
        r_del = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_rec_level=10, delete_key_reset=True
        )
        self.assertTrue(r_del.admitted)
        self.assertEqual(r_del.body_audio_rec_level, 26)
        r_csr = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_rec_level=31, camera_settings_reset_applied=True
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.body_audio_rec_level, 26)

    def test_21_82a_fx3_permanent_non_defeatable_body_limiter(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            limiter_disable_requested=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.body_limiter_always_on)
        self.assertFalse(r.limiter_defeatable)

    def test_22_82a_fx3_xlrh1_handle_audio_on_bypasses_body_reclevel(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=True,
            xlr_h1_input_mode="LINE",
            xlr_h1_agc_mode="MAN",
            xlr_h1_dial_0_to_10=6,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.body_audio_rec_level_greyed_out)
        self.assertIsNone(r.body_audio_rec_level)
        self.assertEqual(r.active_input_source, "xlr_h1_mishoe")
        self.assertEqual(r.xlr_h1_std_level_dbu, 4)
        self.assertEqual(r.channels_count, 2)
        self.assertEqual(r.bit_depth, 24)

    def test_23_82a_fx3_xlrh1_body_override_attempt_blocked_ebusy(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=True,
            attempt_body_rec_level_override=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EBUSY_ERRNO)
        self.assertTrue(r.body_audio_rec_level_greyed_out)

    def test_24_82a_fx3_xlrh1_att_0_10_20_db_maps_minus60_minus50_minus40_dbu(self) -> None:
        for att_db, expected_dbu in ((0, -60), (10, -50), (20, -40)):
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                operation="fx3_xlr_h1_handle",
                xlr_h1_handle_audio_on=True,
                xlr_h1_input_mode="MIC+48V",
                xlr_h1_att_db=att_db,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.xlr_h1_std_level_dbu, expected_dbu)

    def test_25_82a_fx3_xlrh1_link_mode_disables_input2_dial_and_4ch_24bit(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=True,
            xlr_h1_input_mode="MIC",
            xlr_h1_agc_mode="LINK",
            xlr_h1_four_ch_mode=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.xlr_h1_input2_dial_disabled)
        self.assertEqual(r.channels_count, 4)
        self.assertEqual(r.bit_depth, 24)

    def test_26_82a_fx3_xlrh1_handle_audio_off_falls_back_to_internal_mic(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=False,
            body_rec_level=22,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.active_input_source, "internal_stereo_mic")
        self.assertEqual(r.body_audio_rec_level, 22)
        self.assertFalse(r.body_audio_rec_level_greyed_out)

    def test_27_82a_fx3_35mm_mic_preempts_xlrh1_even_when_handle_on(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            mic_35mm_plugged=True,
            xlr_h1_handle_audio_on=True,
            body_rec_level=18,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.active_input_source, "body_35mm_mic")
        self.assertEqual(r.body_audio_rec_level, 18)
        self.assertFalse(r.body_audio_rec_level_greyed_out)
        self.assertEqual(r.channels_count, 2)
        self.assertEqual(r.bit_depth, 16)

    def test_28_82a_fx3_sq_mode_locks_audio_0ch_ebusy(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            shoot_mode="S&Q", xlr_h1_handle_audio_on=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EBUSY_ERRNO)
        self.assertEqual(r.channels_count, 0)
        self.assertTrue(r.body_audio_rec_level_greyed_out)

    def test_29_82a_fx3_xlrh1_invalid_att_or_dial_rejected_einval(self) -> None:
        r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=True,
            xlr_h1_att_db=15,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)
        r2 = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            operation="fx3_xlr_h1_handle",
            xlr_h1_handle_audio_on=True,
            xlr_h1_dial_0_to_10=11,
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p365.EINVAL_ERRNO)

    def test_30_82a_fx6_ch1_to_ch4_input_select_matrix_and_0_99_levels(self) -> None:
        valid_pairs = (
            ("CH1", "INPUT1"),
            ("CH1", "Shoe CH1"),
            ("CH2", "INPUT2"),
            ("CH3", "Off"),
            ("CH3", "Internal MIC"),
            ("CH4", "INPUT2"),
            ("CH4", "Shoe CH2"),
        )
        for ch, src in valid_pairs:
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_audio_input",
                fx6_channel=ch,
                fx6_ch_input_select=src,
                fx6_digital_level_0_99=99,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_digital_level_0_99, 99)

        # CH1 cannot select INPUT2 directly in FX6 matrix
        bad = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_audio_input",
            fx6_channel="CH1",
            fx6_ch_input_select="INPUT2",
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p365.EINVAL_ERRNO)

    def test_31_82a_fx6_3tier_reference_levels_all_steps_admitted(self) -> None:
        for ref_lv in ("-20dB", "-18dB", "-16dB", "-12dB", "EBUL"):
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_audio_input",
                fx6_mic_reference_db=-80,
                fx6_line_input_reference="EBUL",
                fx6_reference_level=ref_lv,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_reference_level, ref_lv)
        self.assertEqual(len(p365.FX6_REF_LEVEL_5_STEPS), 5)

    def test_32_82a_fx6_exact_6step_limiter_mode_disproves_4step_rumor(self) -> None:
        self.assertEqual(len(p365.FX6_LIMITER_MODE_6_STEPS), 6)
        for lim in ("Off", "-6dB", "-9dB", "-12dB", "-15dB", "-17dB"):
            r = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_audio_input",
                fx6_limiter_mode=lim,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_limiter_mode, lim)
            self.assertEqual(r.fx6_limiter_steps_count, 6)
            self.assertTrue(r.limiter_defeatable)

    def test_33_82a_fx6_invalid_level_or_limiter_step_einval(self) -> None:
        r1 = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_audio_input",
            fx6_digital_level_0_99=100,
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p365.EINVAL_ERRNO)
        r2 = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_audio_input",
            fx6_limiter_mode="-3dB",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p365.EINVAL_ERRNO)

    def test_34_82a_cross_profile_operations_return_eopnotsupp(self) -> None:
        r_fx3 = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_profile=p365.BODY_MODEL_FX3, operation="fx6_audio_input"
        )
        self.assertFalse(r_fx3.admitted)
        self.assertEqual(r_fx3.errno_code, p365.EOPNOTSUPP_ERRNO)

        r_fx6 = p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx3_body_audio_rec_level",
        )
        self.assertFalse(r_fx6.admitted)
        self.assertEqual(r_fx6.errno_code, p365.EOPNOTSUPP_ERRNO)

    def test_35_82a_invalid_dispatch_raises_stage82_error(self) -> None:
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                body_profile="FX9"
            )
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                operation="bad_op"
            )
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_audio_reclevel_xlrh1_bypass_vs_fx6_audio_input_hil(
                shoot_mode="Interval"
            )

    def test_36_82a_pillar_a_payload_and_redlines_verified(self) -> None:
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        pa = rep["pillar_a_audio_reclevel_xlrh1_bypass_vs_fx6_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(rep["redlines"]["fx3_xlrh1_bypass_escape_events"], 0)
        self.assertTrue(rep["redlines"]["fx3_xlrh1_body_reclevel_bypass_verified"])
        self.assertEqual(rep["redlines"]["fx6_limiter_mode_steps_count"], 6)

    # =========================================================================
    # Tests 37..56: Sub-Model 82B — [Audio Out Timing], [Volume Settings] &
    #               Exact 5-Option [4ch Audio Monitoring] vs FX6 7-Option / Zero
    #               Physical "MONITOR VOL" Button
    # =========================================================================

    def test_37_82b_fx3_audio_out_timing_live_default_and_lip_sync(self) -> None:
        r_live = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_audio_out_timing", audio_out_timing="Live"
        )
        self.assertTrue(r_live.admitted)
        self.assertEqual(r_live.audio_out_timing, "Live")
        self.assertEqual(r_live.audio_out_timing_delay_ms, 0.0)
        self.assertTrue(r_live.audio_out_timing_resettable)

        r_lip = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_audio_out_timing", audio_out_timing="Lip Sync"
        )
        self.assertTrue(r_lip.admitted)
        self.assertEqual(r_lip.audio_out_timing, "Lip Sync")
        self.assertGreater(r_lip.audio_out_timing_delay_ms, 0.0)

    def test_38_82b_fx3_audio_out_timing_resettable_to_live_and_sq_locked(self) -> None:
        r_rst = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_audio_out_timing",
            audio_out_timing="Lip Sync",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.audio_out_timing, "Live")

        r_sq = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_audio_out_timing", shoot_mode="S&Q"
        )
        self.assertFalse(r_sq.admitted)
        self.assertEqual(r_sq.errno_code, p365.EBUSY_ERRNO)

    def test_39_82b_fx3_audio_out_timing_invalid_rejected_einval(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_audio_out_timing", audio_out_timing="Processed"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_40_82b_fx3_volume_settings_0_to_15_default_7_and_reset_resistant(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_volume_settings",
            volume_level=14,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.volume_level, 14)
        self.assertFalse(r.volume_resettable_by_camera_reset)

    def test_41_82b_fx3_volume_settings_initialize_restores_7(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_volume_settings",
            volume_level=15,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.volume_level, 7)

    def test_42_82b_fx3_volume_settings_speaker_howl_guard_and_bounds(self) -> None:
        r_howl = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_volume_settings",
            volume_level=12,
            headphone_plugged=False,
            xlr_h1_attached=True,
        )
        self.assertTrue(r_howl.admitted)
        self.assertTrue(r_howl.speaker_feedback_howl_risk)

        r_bad = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_volume_settings", volume_level=16
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p365.EINVAL_ERRNO)

    def test_43_82b_fx3_4ch_monitoring_exact_5_options_admitted(self) -> None:
        self.assertEqual(len(p365.FX3_4CH_MONITORING_5_OPTIONS), 5)
        for opt in ("CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"):
            r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
                operation="fx3_4ch_monitoring", monitoring_4ch_option=opt
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.monitoring_4ch_option, opt)
            self.assertEqual(r.monitoring_options_count, 5)
            self.assertEqual(r.headphone_channels_count, 2)
            self.assertTrue(r.governs_headphone_and_rear_speaker)

    def test_44_82b_fx3_4ch_monitoring_errata_strings_rejected_eopnotsupp(self) -> None:
        for err_opt in ("CH1/CH2 mono mix", "CH1+2/CH3+4", "All", "MIX ALL", "CH1"):
            r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
                operation="fx3_4ch_monitoring", monitoring_4ch_option=err_opt
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)

    def test_45_82b_fx3_4ch_monitoring_reset_resistant_and_initialize_clears(self) -> None:
        r_csr = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_4ch_monitoring",
            monitoring_4ch_option="CH2/CH2",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.monitoring_4ch_option, "CH2/CH2")
        self.assertFalse(r_csr.monitoring_4ch_resettable_by_camera_reset)

        r_init = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_4ch_monitoring",
            monitoring_4ch_option="CH2/CH2",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.monitoring_4ch_option, "CH1/CH2")

    def test_46_82b_fx3_4ch_monitoring_independent_of_hdmi_4ch_output(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_4ch_monitoring",
            monitoring_4ch_option="CH1/CH1",
            hdmi_4ch_audio_output="CH3/CH4",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.monitoring_4ch_option, "CH1/CH1")
        self.assertEqual(r.hdmi_4ch_audio_output, "CH3/CH4")
        self.assertEqual(r.hdmi_channels_count, 2)
        self.assertEqual(r.sdi_channels_count, 0)

    def test_47_82b_fx3_invalid_hdmi_4ch_output_einval(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_4ch_monitoring",
            monitoring_4ch_option="CH1/CH2",
            hdmi_4ch_audio_output="CH1+3/CH2+4",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_48_82b_fx6_monitor_ch_exact_7_options_and_sdi_4ch(self) -> None:
        self.assertEqual(len(p365.FX6_MONITOR_CH_7_OPTIONS), 7)
        for opt in ("CH1", "CH2", "CH3", "CH4", "CH1/CH2", "CH3/CH4", "MIX ALL"):
            r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_audio_output",
                monitoring_4ch_option=opt,
                volume_level=45,
                fx6_headphone_out_mode="Stereo",
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.monitoring_options_count, 7)
            self.assertEqual(r.sdi_channels_count, 4)
            self.assertEqual(r.hdmi_channels_count, 2)

    def test_49_82b_fx6_headphone_out_mono_and_volume_0_50(self) -> None:
        for vol in (0, 25, 50):
            r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_audio_output",
                monitoring_4ch_option="CH3/CH4",
                volume_level=vol,
                fx6_headphone_out_mode="Mono",
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_headphone_out_mode, "Mono")
            self.assertEqual(r.volume_level, vol)

    def test_50_82b_fx6_zero_physical_monitor_vol_button_enodev(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_audio_output",
            request_physical_monitor_vol_button=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.ENODEV_ERRNO)
        self.assertFalse(r.fx6_physical_monitor_vol_button_present)

    def test_51_82b_fx6_invalid_volume_or_headphone_mode_einval(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_audio_output",
            volume_level=51,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_52_82b_cross_profile_operations_return_eopnotsupp(self) -> None:
        r_fx3 = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            body_profile=p365.BODY_MODEL_FX3, operation="fx6_audio_output"
        )
        self.assertFalse(r_fx3.admitted)
        self.assertEqual(r_fx3.errno_code, p365.EOPNOTSUPP_ERRNO)

        r_fx6 = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx3_4ch_monitoring",
        )
        self.assertFalse(r_fx6.admitted)
        self.assertEqual(r_fx6.errno_code, p365.EOPNOTSUPP_ERRNO)

    def test_53_82b_invalid_dispatch_raises_stage82_error(self) -> None:
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
                operation="unknown"
            )

    def test_54_82b_negative_volume_rejected_einval(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_volume_settings", volume_level=-1
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_55_82b_fx3_4ch_monitoring_unknown_string_einval(self) -> None:
        r = p365.simulate_audio_out_timing_volume_and_4ch_monitoring_hil(
            operation="fx3_4ch_monitoring", monitoring_4ch_option="CH9/CH10"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_56_82b_pillar_b_payload_and_redlines_verified(self) -> None:
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        pb = rep["pillar_b_audio_out_timing_volume_4ch_mon_vs_fx6_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(rep["redlines"]["fx3_4ch_monitoring_options_count"], 5)
        self.assertTrue(rep["redlines"]["fx3_3option_errata_corrected"])
        self.assertEqual(rep["redlines"]["fx3_4ch_monitoring_reset_wipe_events"], 0)
        self.assertFalse(rep["redlines"]["fx6_physical_monitor_vol_button_present"])

    # =========================================================================
    # Tests 57..76: Sub-Model 82C — Exact 4 Active [Touch Operation] Items vs
    #               Dormant [Touch Panel/Pad]/[Touch Shutter]/[Touch AE] & FX6
    # =========================================================================

    def test_57_82c_fx3_touch_setup_exact_4_active_items_and_defaults(self) -> None:
        self.assertEqual(len(p365.FX3_TOUCH_SETUP_4_ITEMS), 4)
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_setup"
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.touch_setup_active_items_count, 4)
        self.assertEqual(r.touch_operation, "On")
        self.assertEqual(r.touch_sensitivity, "Standard")
        self.assertEqual(r.touch_func_in_shooting, "Touch Tracking")
        self.assertEqual(r.swipe_up, "Open the Fn Menu")
        self.assertTrue(r.swipe_up_active)
        self.assertFalse(r.resettable_via_camera_settings_reset)
        self.assertTrue(r.cleared_only_by_initialize)

    def test_58_82c_fx3_touch_setup_all_4_items_reset_resistant(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_setup",
            touch_operation="On: Playback Only",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Touch Focus",
            swipe_up="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.touch_operation, "On: Playback Only")
        self.assertEqual(r.touch_sensitivity, "Sensitive")
        self.assertEqual(r.touch_func_in_shooting, "Touch Focus")
        self.assertEqual(r.swipe_up, "Off")
        self.assertFalse(r.swipe_up_active)

    def test_59_82c_fx3_touch_setup_initialize_clears_all_4_items(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_setup",
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Off",
            swipe_up="Off",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.touch_operation, "On")
        self.assertEqual(r.touch_sensitivity, "Standard")
        self.assertEqual(r.touch_func_in_shooting, "Touch Tracking")
        self.assertEqual(r.swipe_up, "Open the Fn Menu")

    def test_60_82c_fx3_touch_func_in_shooting_shared_across_still_movie_sq(self) -> None:
        for mode in ("Still", "Movie", "S&Q"):
            r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
                operation="fx3_touch_tap_in_shooting",
                shoot_mode=mode,
                af_mf_mode="AF",
                touch_func_in_shooting="Touch Tracking",
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.touch_func_in_shooting, "Touch Tracking")

    def test_61_82c_fx3_mf_mode_disables_touch_tracking_eopnotsupp(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_tap_in_shooting",
            af_mf_mode="MF",
            touch_func_in_shooting="Touch Tracking",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)

        r_tf = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_tap_in_shooting",
            af_mf_mode="MF",
            touch_func_in_shooting="Touch Focus",
        )
        self.assertTrue(r_tf.admitted)

    def test_62_82c_fx3_playback_only_or_off_suppresses_shooting_tap_ebusy(self) -> None:
        for op_mode in ("On: Playback Only", "Off"):
            r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
                operation="fx3_touch_tap_in_shooting",
                touch_operation=op_mode,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p365.EBUSY_ERRNO)
            self.assertFalse(r.swipe_up_active)

    def test_63_82c_fx3_dormant_touch_panel_pad_100pct_masked_eopnotsupp(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="dormant_touch_panel_pad"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.dormant_touch_panel_pad_exposed)

    def test_64_82c_fx3_dormant_touch_shutter_100pct_masked_eopnotsupp(self) -> None:
        for mode in ("Still", "Movie", "S&Q"):
            r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
                operation="dormant_touch_shutter", shoot_mode=mode
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.dormant_touch_shutter_exposed)

    def test_65_82c_fx3_dormant_touch_ae_100pct_masked_eopnotsupp(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="dormant_touch_ae"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.dormant_touch_ae_exposed)

    def test_66_82c_fx3_spot_metering_focus_point_link_static_only(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_spot_metering_link",
            spot_metering_point="Focus Point Link",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.spot_link_tracks_moving_box)

    def test_67_82c_fx3_spot_metering_cannot_follow_moving_tracking_box(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_spot_metering_link",
            spot_metering_point="Focus Point Link",
            request_follow_moving_tracking_box=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.spot_link_tracks_moving_box)

    def test_68_82c_fx3_swipe_up_disabled_when_swipe_up_off(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_setup", swipe_up="Off"
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.swipe_up_active)

    def test_69_82c_fx6_touch_operation_and_spot_focus_in_mf_admitted(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_touch_operation",
            fx6_touch_function_in_mf="Spot Focus",
            invoke_touch_in_mf=True,
        )
        self.assertTrue(r.admitted)
        self.assertIsNone(r.fx6_spot_focus_disabled_reason)
        self.assertTrue(r.fx6_big6_and_full_menu_touch_supported)

    def test_70_82c_fx6_spot_focus_blocked_manual_lens_desqueeze_or_focus_mag(self) -> None:
        for flag, expected_reason in (
            ("fx6_manual_lens_switch", "manual_lens_switch"),
            ("fx6_desqueeze_active", "desqueeze_active"),
            ("fx6_focus_magnifier_active", "focus_magnifier_active"),
        ):
            r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
                body_profile=p365.BODY_MODEL_FX6,
                fw_version=p365.FW_VER_601,
                operation="fx6_touch_operation",
                fx6_touch_function_in_mf="Spot Focus",
                invoke_touch_in_mf=True,
                **{flag: True},
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p365.EBUSY_ERRNO)
            self.assertEqual(r.fx6_spot_focus_disabled_reason, expected_reason)

    def test_71_82c_fx6_tracking_af_and_ver500_vs_ver601_big6_touch(self) -> None:
        r500 = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_500,
            operation="fx6_touch_operation",
            fx6_touch_function_in_mf="Tracking AF",
        )
        self.assertTrue(r500.admitted)
        self.assertFalse(r500.fx6_big6_and_full_menu_touch_supported)

        r601 = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_touch_operation",
            fx6_touch_function_in_mf="Tracking AF",
        )
        self.assertTrue(r601.admitted)
        self.assertTrue(r601.fx6_big6_and_full_menu_touch_supported)

    def test_72_82c_fx3_invalid_touch_enum_einval(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            operation="fx3_touch_setup", touch_func_in_shooting="Touch Shutter"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_73_82c_fx6_invalid_touch_enum_einval(self) -> None:
        r = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_touch_operation",
            touch_operation="On: Playback Only",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_74_82c_cross_profile_operations_eopnotsupp(self) -> None:
        r1 = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX3, operation="fx6_touch_operation"
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p365.EOPNOTSUPP_ERRNO)

        r2 = p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx3_touch_setup",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p365.EOPNOTSUPP_ERRNO)

    def test_75_82c_invalid_dispatch_raises_stage82_error(self) -> None:
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_touch_operation_dormant_shutter_ae_vs_fx6_hil(
                af_mf_mode="DMF"
            )

    def test_76_82c_pillar_c_payload_and_redlines_verified(self) -> None:
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        pc = rep["pillar_c_touch_operation_4item_vs_dormant_shutter_ae_fx6_hil"]
        self.assertTrue(pc["passed"])
        self.assertEqual(rep["redlines"]["fx3_touch_setup_active_items_count"], 4)
        self.assertEqual(
            rep["redlines"]["fx3_dormant_touch_shutter_ae_pad_exposed_events"], 0
        )
        self.assertEqual(rep["redlines"]["fx3_ilc2210_touch_shutter_hits"], 0)
        self.assertEqual(rep["redlines"]["fx3_ilc2210_touch_ae_hits"], 0)
        self.assertFalse(rep["redlines"]["fx3_spot_link_tracks_moving_box"])

    # =========================================================================
    # Tests 77..95: Sub-Model 82D — [PC Remote Function] -> [Remote Shoot
    #               Setting], PTP/PTP-IP Destination Only RAM vs Slot 1
    #               EROFS=30 Firewall & FX6 Camera Remote Control
    # =========================================================================

    def test_77_82d_fx3_v1_vs_v2_plus_menu_evolution_and_dest_enums(self) -> None:
        r_v1 = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            fw_version=p365.FW_VER_101,
            operation="fx3_remote_shoot_config",
            still_img_save_dest="PC Only",
        )
        self.assertTrue(r_v1.admitted)
        self.assertEqual(r_v1.menu_path, "Transfer/Remote -> [PC Remote Function]")
        self.assertTrue(r_v1.ram_direct_transfer_active)

        r_v7 = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            fw_version=p365.FW_VER_702,
            operation="fx3_remote_shoot_config",
            still_img_save_dest="Destination Only",
        )
        self.assertTrue(r_v7.admitted)
        self.assertEqual(
            r_v7.menu_path, "Network -> [Cnct./Remote Sht.] -> [Remote Shoot Setting]"
        )
        self.assertTrue(r_v7.ram_direct_transfer_active)

    def test_78_82d_fx3_v2_plus_rejects_v1_pc_only_string_einval(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            fw_version=p365.FW_VER_702,
            operation="fx3_remote_shoot_config",
            still_img_save_dest="PC Only",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_79_82d_fx3_remote_shoot_reset_resistant_to_camera_settings_reset(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_shoot_config",
            still_img_save_dest="Destination Only",
            save_image_size="Original",
            raw_j_save_image="RAW & JPEG",
            raw_h_save_image="RAW Only",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.still_img_save_dest, "Destination Only")
        self.assertEqual(r.save_image_size, "Original")
        self.assertEqual(r.raw_j_save_image, "RAW & JPEG")
        self.assertEqual(r.raw_h_save_image, "RAW Only")
        self.assertFalse(r.resettable_via_camera_settings_reset)

    def test_80_82d_fx3_reset_network_set_and_initialize_restore_factory_dest_camera(self) -> None:
        for flag in ("reset_network_set_applied", "initialize_applied"):
            r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
                operation="fx3_remote_shoot_config",
                still_img_save_dest="Destination Only",
                save_image_size="Original",
                **{flag: True},
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.still_img_save_dest, "Dest.+Camera")
            self.assertEqual(r.save_image_size, "2M")
            self.assertFalse(r.ram_direct_transfer_active)

    def test_81_82d_fx3_connected_state_locks_save_dest_change_ebusy(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_shoot_config",
            connection_state="CONNECTED",
            change_save_dest_while_connected=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EBUSY_ERRNO)

        r_disc = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_shoot_config",
            connection_state="DISCONNECTED",
            change_save_dest_while_connected=True,
        )
        self.assertTrue(r_disc.admitted)

    def test_82_82d_fx3_destination_only_usb_sicd_cardless_ram_capture(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Destination Only",
            transport_protocol="PTP_USB_SICD",
            card_inserted_slot1=False,
            release_wo_card="Disable",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.usb_pid_vid, "054c:0d2b")
        self.assertTrue(r.ram_direct_transfer_active)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.rf_tx_packets, 0)

    def test_83_82d_fx3_destination_only_ptpip_usblan_cardless_zero_rf(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Destination Only",
            transport_protocol="PTP_IP_TCP_15740",
            wired_usb_lan=True,
            airplane_mode="On",
            card_inserted_slot1=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.ptp_ip_port, 15740)
        self.assertTrue(r.ram_direct_transfer_active)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.rf_tx_packets, 0)

    def test_84_82d_fx3_wifi_ptpip_blocked_when_airplane_mode_on_enodev(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Destination Only",
            transport_protocol="PTP_IP_TCP_15740",
            wired_usb_lan=False,
            airplane_mode="On",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.ENODEV_ERRNO)
        self.assertFalse(r.ram_direct_transfer_active)

    def test_85_82d_fx3_factory_default_dest_plus_camera_cardless_refused_enodev(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Dest.+Camera",
            card_inserted_slot1=False,
            release_wo_card="Enable",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.ENODEV_ERRNO)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_86_82d_fx3_dest_plus_camera_with_card_hits_tier0_slot1_erofs_30(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Dest.+Camera",
            card_inserted_slot1=True,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EROFS_ERRNO)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertTrue(r.slot1_erofs_enforced)

    def test_87_82d_fx3_camera_only_cardless_and_slot1_erofs_30(self) -> None:
        r_nocard = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Camera Only",
            card_inserted_slot1=False,
        )
        self.assertFalse(r_nocard.admitted)
        self.assertEqual(r_nocard.errno_code, p365.ENODEV_ERRNO)

        r_card = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_capture",
            still_img_save_dest="Camera Only",
            card_inserted_slot1=True,
        )
        self.assertFalse(r_card.admitted)
        self.assertEqual(r_card.errno_code, p365.EROFS_ERRNO)
        self.assertEqual(r_card.slot1_data_sector_writes, 0)

    def test_88_82d_fx3_v1_pc_only_ram_capture_vs_pc_plus_camera_erofs(self) -> None:
        r_ram = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            fw_version=p365.FW_VER_101,
            operation="fx3_remote_capture",
            still_img_save_dest="PC Only",
            card_inserted_slot1=False,
        )
        self.assertTrue(r_ram.admitted)
        self.assertTrue(r_ram.ram_direct_transfer_active)
        self.assertEqual(r_ram.slot1_data_sector_writes, 0)

        r_blk = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            fw_version=p365.FW_VER_101,
            operation="fx3_remote_capture",
            still_img_save_dest="PC+Camera",
            card_inserted_slot1=True,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p365.EROFS_ERRNO)

    def test_89_82d_fx6_camera_remote_control_ptpip_15740_admitted(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_camera_remote_control",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.ptp_ip_port, 15740)
        self.assertFalse(r.fx6_still_img_save_dest_ui_exposed)
        self.assertEqual(r.rf_tx_packets, 0)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_90_82d_fx6_still_img_save_dest_ui_masked_eopnotsupp(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx6_camera_remote_control",
            request_fx6_save_dest_ui=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_still_img_save_dest_ui_exposed)

    def test_91_82d_cross_profile_operations_return_eopnotsupp(self) -> None:
        r1 = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            body_profile=p365.BODY_MODEL_FX3, operation="fx6_camera_remote_control"
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p365.EOPNOTSUPP_ERRNO)

        r2 = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            body_profile=p365.BODY_MODEL_FX6,
            fw_version=p365.FW_VER_601,
            operation="fx3_remote_capture",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p365.EOPNOTSUPP_ERRNO)

    def test_92_82d_all_save_image_sizes_and_raw_options_admitted(self) -> None:
        for sz in ("Original", "2M"):
            for rj in ("RAW & JPEG", "JPEG Only", "RAW Only"):
                r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
                    operation="fx3_remote_shoot_config",
                    still_img_save_dest="Destination Only",
                    save_image_size=sz,
                    raw_j_save_image=rj,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.save_image_size, sz)
                self.assertEqual(r.raw_j_save_image, rj)

    def test_93_82d_invalid_save_image_size_or_raw_option_einval(self) -> None:
        r = p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
            operation="fx3_remote_shoot_config",
            still_img_save_dest="Destination Only",
            save_image_size="4M",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p365.EINVAL_ERRNO)

    def test_94_82d_invalid_dispatch_raises_stage82_error(self) -> None:
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
                transport_protocol="BLE"
            )
        with self.assertRaises(p365.Stage82Phase365Error):
            p365.simulate_remote_shoot_setting_ptp_vs_slot1_erofs_hil(
                connection_state="PAIRING"
            )

    def test_95_82d_pillar_d_payload_and_redlines_verified(self) -> None:
        rep = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        pd = rep["pillar_d_remote_shoot_setting_ptp_vs_slot1_erofs_fx6_hil"]
        self.assertTrue(pd["passed"])
        self.assertEqual(rep["redlines"]["fx3_ptp_usb_vid_pid"], "054c:0d2b")
        self.assertEqual(rep["redlines"]["fx3_ptpip_tcp_port"], 15740)
        self.assertEqual(
            rep["redlines"]["fx3_remote_shoot_factory_default_dest"], "Dest.+Camera"
        )
        self.assertEqual(
            rep["redlines"]["fx3_remote_shoot_dest_only_ram_writes_slot1"], 0
        )
        self.assertEqual(
            rep["redlines"]["fx3_slot1_remote_shoot_write_bypass_events"], 0
        )
        self.assertFalse(rep["redlines"]["fx6_still_img_save_dest_ui_exposed"])

    # =========================================================================
    # Tests 96..100: Determinism, Digest Distinction, CLI, Portability & Suite
    #                82/82 Integration
    # =========================================================================

    def test_96_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            force_clean_room=True
        )
        r_f2 = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["audit_digest_sha256"], r_f2["audit_digest_sha256"])
        self.assertEqual(r_f1["audit_digest_sha256"], r_f3["audit_digest_sha256"])
        self.assertRegex(r_f1["audit_digest_sha256"], r"^[0-9a-f]{64}$")

        r_dl1 = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root=None
        )
        r_dl2 = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
            work_root="/nonexistent/phase365_stage82_test"
        )
        self.assertEqual(r_dl1["audit_digest_sha256"], r_dl2["audit_digest_sha256"])

        # Normal donor digest differs from clean-room digest when local donors exist
        r_norm = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["audit_digest_sha256"], r_f1["audit_digest_sha256"]
            )
            self.assertNotEqual(
                r_norm["audit_digest_sha256"], r_dl1["audit_digest_sha256"]
            )

    def test_97_standalone_cli_self_test_summary_json_and_help(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p365.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 365 Stage 82/82", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p365.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "82/82")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p365.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("82/82", buf_help.getvalue())

    def test_98_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p365.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_99_suite_default_config_and_82_of_82_stage_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase365_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil
        )
        self.assertTrue(default_cfg.include_stage82)
        self.assertTrue(
            default_cfg.stage82_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s82 = rep["stage82_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil"]
        self.assertTrue(s82["all_checks_passed"])
        self.assertEqual(s82["phase_number"], 365)
        self.assertEqual(s82["milestone"], "82/82")
        self.assertTrue(s82["is_82nd_stage_milestone"])
        self.assertEqual(s82["raw_firmware_bytes_leaked"], 0)

        stage_keys = [
            f for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Base 3 stages (stage1, stage2, stage3) + optional phase flags must reach >= 82
        self.assertGreaterEqual(len(stage_keys) + 3, 82)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil=",
            buf.getvalue(),
        )
        self.assertIn("m82=82/82", buf.getvalue())

        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc2 = suite.main([*_FAST_CLI_FLAGS, "--skip-stage82", "--json"])
        self.assertEqual(rc2, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertNotIn(
            "stage82_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil",
            rep_skip,
        )

        buf_skip_p = io.StringIO()
        with contextlib.redirect_stdout(buf_skip_p):
            rc3 = suite.main([*_FAST_CLI_FLAGS, "--skip-phase365", "--json"])
        self.assertEqual(rc3, 0)
        rep_skip_p = json.loads(buf_skip_p.getvalue())
        self.assertNotIn(
            "stage82_realhw_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_hil",
            rep_skip_p,
        )

        # CLI subprocess execution check (PYTHONDONTWRITEBYTECODE=1 + -B)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p365.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Phase 365 Stage 82/82", proc.stdout)

        # Tamper detection on milestone probe fails suite check if mutated
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        with unittest.mock.patch.object(
            p365,
            "run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation",
            wraps=p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation,
        ) as m_run:
            real = p365.run_phase365_audioreclevel_4chmon_touchfunc_remoteshoot_ptp_coemulation(
                force_clean_room=True
            )
            bad = dict(real)
            bad["milestone"] = "81/81"
            m_run.return_value = bad
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
