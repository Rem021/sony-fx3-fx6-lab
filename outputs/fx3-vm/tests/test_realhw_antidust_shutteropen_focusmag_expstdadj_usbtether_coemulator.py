#!/usr/bin/env python3
"""Unit tests for Phase 362 (Stage 81 — 81/81 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-71:
- 81A: Dormant `[Anti-Dust Function]` / `[Shutter When Pwr OFF]` (`_f 0x7495`/
  `0x709f`, `PID_SET_IMAGE_SENSOR_BARRIER` masked out by `ALCIN_UUD` ->
  `EOPNOTSUPP=95`, `ilc/2210` `0` hits), mechanical focal-plane curtain ALWAYS
  `OPEN` at power-OFF, active `Setup -> [Setup Option] -> [Sensor Cleaning]`
  (`_f 0x67d6`, legacy `Cleaning Mode` `0xe7d7`, `NP-FZ100 >= 51%` gate ->
  `EAGAIN=11` below `51%`, IBIS ultrasonic shake + mandatory physical power-OFF
  prompt) vs FX6 (`0` `shutter_when_power_off` symbols, zero mechanical shutter,
  zero IBIS cleaning, CMOS sealed behind `1/4..1/128 + CLEAR` variable `e-ND` +
  IR-cut glass, `Technical > APR`),
- 81B: `[Focus Magnifier]` full 5-item `[Focus Assistant]` cluster (all Reset-
  resistant `Not available` in Ver. 2.00+..7.02 vs Ver. 1.01), `12.1MP` exact
  ratios (Still FF `x1.0 -> x2.1 -> x4.1`, Still APS-C `x1.0 -> x1.5 -> x3.0`,
  Movie/`S&Q` `x1.0 <-> x4.0`; dormant high-MP ratios `x1.6..x6.1` ->
  `EOPNOTSUPP=95`), `[Focus Magnif. Time]` (`2 Sec`/`5 Sec`/`No Limit`),
  Still-only `[AF in Focus Mag.]` & `[Auto Magnifier in MF]`, continuous
  `MOVIE REC` operation (`0` mutex), zero crop on internal XAVC or Clean-HDMI
  (`HDMI Info. Display = Off`), coexistence (`Peaking`, Ver. 7.00+ `Bright
  Monitoring`, `De-Squeeze`) & suppression (`Marker`, `Switch V/H AF Area`,
  `AF Illuminator`) vs FX6 `Focus Magnifier x3/x6` & Ver. 6.0+ `Focus Mag
  Button Target` (`VF: x3/x6` vs `HDMI: x2/x4`, SDI & internal MXF clean),
- 81C: `[Exposure Std. Adjust]` 5 metering modes (`Multi`, `Center`, `Spot`,
  `Entire Screen Avg.`, `Highlight`), `-1..+1 EV` in `1/6 EV` (`13` steps;
  dormant `1/8 EV` -> `EOPNOTSUPP=95`), Reset-resistant (`Not available`,
  `[Initialize]`-only), warning icon, `M.M.` & Spot AEL shift without altering
  `[Exposure Comp.]` or EXIF `ExposureBiasValue`, bracket counter reset, AE
  shift in `P/A/S` & `Flexible ISO + ISO AUTO` vs `M.M.`-only in `Cine EI` /
  `Cine EI Quick` / `M + Fixed ISO` vs FX6 `Auto Exposure > Level` (`-3.0..+3.0`
  in `0.25 EV` = `25` steps, disproving `±2.0 EV` rumor, per-LUT `Base Look >
  AE Level Offset`, `AE Speed -99..+99`),
- 81D: Wired smartphone `[USB-LAN/Tethering]` (`libNetServiceTethering.so` +
  `libTetheringResource.so` + `cdc_ncm`/`cdc_ether`/`rndis_host`/`ipheth.ko` +
  `dhcpcd`) enabling `RTMP/RTMPS/SRT` & `FTP` with `[Airplane Mode] = On`
  (`rf_tx_packets == 0`), `Creators' App` streaming wizard blocked over USB,
  `Monitor & Control` Ver. 4.00+ wired USB disables Timecode/Focus Map/LUT
  import, dual-USB simultaneous comms blocked (`EBUSY=16`), `[Reset Network
  Set.]` requires immediate `Airplane Mode = On` re-arm, hard `EROFS=30` +
  `usbgmscif_setReadOnly` firewall blocking `MTP` (`Slot 1`-locked) & `MSC`
  (`Single`/`Multi` LUN) writes to Tier-0 `Slot 1` (`slot1_sector_writes == 0`)
  vs FX6 `Network > USB Tethering` (`FX6 libInfraUsbCmn.so` links `usbg_iap.ko`
  `CUsbGadgetIAP` vs `0` in `FX3 libInfraUsbCmn.so`/`FX3 appFw.so`)
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
import realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulator as p362  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..80 for Stage 81 isolation tests."""
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
]


class TestPhase362Stage81CoEmulator(unittest.TestCase):
    # -----------------------------------------------------------------------
    # 01..16: Schema, Redlines, 26-Donor O_RDONLY & Clean-Room Fallback
    # -----------------------------------------------------------------------

    def test_01_schema_milestone_and_hardware_redline_constants(self) -> None:
        self.assertEqual(
            p362.SCHEMA_ID,
            "phase362_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation_v1",
        )
        self.assertEqual(p362.PHASE_NUMBER, 362)
        self.assertEqual(p362.STAGE_INDEX, 81)
        self.assertEqual(p362.STAGE_TOTAL, 81)
        self.assertEqual(p362.MILESTONE_LABEL, "81/81")
        self.assertTrue(p362.IS_81ST_STAGE_MILESTONE)
        self.assertTrue(p362.P8_CP_MUTATION_FORBIDDEN)
        self.assertEqual(p362.NOP_COUNT, 0)
        self.assertEqual(p362.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p362.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p362.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p362.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p362.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p362.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertEqual(p362.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p362.RF_TX_PACKETS, 0)
        self.assertEqual(p362.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_specs_exact_23_compact_plus_3_window_equals_26(self) -> None:
        self.assertEqual(len(p362.PHASE362_COMPACT_DONORS), 23)
        self.assertEqual(len(p362.PHASE362_WINDOW_DONORS), 3)
        names = [d.name for d in p362.PHASE362_COMPACT_DONORS] + [
            w.name for w in p362.PHASE362_WINDOW_DONORS
        ]
        self.assertEqual(len(names), 26)
        self.assertEqual(len(set(names)), 26)

    def test_03_compact_donor_specs_validate_64hex_sha_and_max_1mib(self) -> None:
        for spec in p362.PHASE362_COMPACT_DONORS:
            self.assertGreater(spec.expected_size, 0)
            self.assertLessEqual(spec.expected_size, 1048576)
            self.assertRegex(spec.expected_sha256, r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(len(spec.required_tokens), 1)

    def test_04_window_donor_specs_validate_head4k_and_absent_checks(self) -> None:
        for wspec in p362.PHASE362_WINDOW_DONORS:
            self.assertGreater(wspec.expected_size, 1048576)
            self.assertRegex(wspec.head4k_sha256, r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(len(wspec.windows), 1)
        # Verify FX3 appFw has absent_windows and FX6 has 0 shutter_when_power_off
        fx6_appfw = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx6_appfw")
        self.assertGreaterEqual(len(fx6_appfw.absent_windows), 1)

    def test_05_clean_room_fallback_with_work_root_none(self) -> None:
        donor_audit = p362.inspect_phase362_wave71_donors(work_root=None)
        self.assertEqual(donor_audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(donor_audit["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertFalse(donor_audit["work_root_available"])
        self.assertEqual(donor_audit["total_donors_count"], 26)
        self.assertTrue(donor_audit["all_donors_verified"])
        self.assertEqual(donor_audit["raw_firmware_bytes_leaked"], 0)

    def test_06_clean_room_fallback_with_nonexistent_work_root_and_sentinel(self) -> None:
        for wr in (Path("/nonexistent/fx3/wave71/work"), "__fx3_fx6_clean_room_donor_disabled__"):
            audit = p362.inspect_phase362_wave71_donors(work_root=wr)
            self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(audit["all_donors_verified"])
            self.assertEqual(audit["raw_firmware_bytes_leaked"], 0)

    def test_07_env_flags_force_clean_room_both_variables(self) -> None:
        for key in ("FX3_FX6_FORCE_CLEAN_ROOM", "FX3_CLEAN_ROOM_TEST"):
            rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
                env={key: "1"}
            )
            self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep["all_checks_passed"])

    def test_08_env_mac_work_root_disabled_sentinel(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            env={"FX3_FX6_MAC_WORK_ROOT": "__fx3_fx6_clean_room_donor_disabled__"}
        )
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep["all_checks_passed"])

    def test_09_local_donor_o_rdonly_audit_when_real_work_present(self) -> None:
        if IS_CI or p362.is_forced_clean_room():
            self.skipTest("CI / clean-room override active")
        root = p362.resolve_mac_work_root()
        if root is None or not root.exists():
            self.skipTest("Local Mac work donor tree absent")
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(rep["donor_audit"]["donor_access_mode"], "O_RDONLY")
        self.assertEqual(rep["donor_audit"]["total_donors_count"], 26)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_10_bounded_window_read_rejects_oversize_request(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"X" * 8192)
            tf.flush()
            with self.assertRaises(p362.Stage81Phase362Error):
                p362._read_bounded_window_o_rdonly(Path(tf.name), 0, 4097)

    def test_11_compact_reader_rejects_oversize_file(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.truncate(1048577)
            with self.assertRaises(p362.Stage81Phase362Error):
                p362._read_full_compact_o_rdonly(Path(tf.name))

    def test_12_tampered_local_compact_donor_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for s in p362.PHASE362_COMPACT_DONORS:
                p = root / s.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * s.expected_size)
            for w in p362.PHASE362_WINDOW_DONORS:
                p = root / w.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "wb") as f:
                    f.truncate(w.expected_size)
            with self.assertRaises(p362.Stage81Phase362Error):
                p362.inspect_phase362_wave71_donors(work_root=root, force_clean_room=False)

    def test_13_tampered_window_donor_missing_needle_or_forbidden_needle_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tf = Path(td) / "dummy.bin"
            tf.write_bytes(b"\x00" * 8192)
            size, head4k, win = p362._read_bounded_window_o_rdonly(tf, 0, 4096)
            self.assertEqual(size, 8192)
            self.assertEqual(len(head4k), 4096)
            self.assertEqual(len(win), 4096)

    def test_14_strip_wall_clock_recursively_strips_elapsed_seconds(self) -> None:
        raw = {"a": 1, "elapsed_seconds": 0.5, "nested": [{"elapsed_seconds": 1.2, "ok": True}]}
        stripped = p362._strip_wall_clock(raw)
        self.assertEqual(stripped, {"a": 1, "nested": [{"ok": True}]})

    def test_15_deterministic_digest_clean_room_vs_work_root_none_match(self) -> None:
        r1 = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        r2 = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r3 = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            work_root=None,
            env={},
        )
        r4 = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            work_root=Path("/nonexistent/fx3/wave71/work"),
            env={},
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r3["audit_digest_sha256"], r4["audit_digest_sha256"])
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)

    def test_16_milestone_probe_exact_stage81_metadata(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        probe = rep["stage81_milestone_probe"]
        self.assertEqual(probe["phase_number"], 362)
        self.assertEqual(probe["stage_index"], 81)
        self.assertEqual(probe["stage_total"], 81)
        self.assertEqual(probe["milestone"], "81/81")
        self.assertTrue(probe["is_81st_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-71")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    # -----------------------------------------------------------------------
    # 17..35: Sub-Model 81A — Dormant Anti-Dust / Shutter When Pwr OFF,
    #         Always-Open Curtain, Sensor Cleaning >=51% & FX6 Sealed e-ND
    # -----------------------------------------------------------------------

    def test_17_81a_fx3_curtain_always_open_at_power_off(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            body_profile=p362.BODY_MODEL_FX3,
            fw_version=p362.FW_VER_702,
            operation="power_off_curtain_state",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.curtain_state_at_power_off, "OPEN")
        self.assertTrue(res.curtain_always_open)
        self.assertEqual(res.curtain_closed_at_power_off_events, 0)
        self.assertFalse(res.anti_dust_menu_exposed)
        self.assertFalse(res.shutter_when_pwr_off_exposed)
        self.assertTrue(res.mechanical_shutter_present)

    def test_18_81a_fx3_dormant_anti_dust_and_shutter_pwr_off_rejected_eopnotsupp(self) -> None:
        for op in ("anti_dust_function", "shutter_when_pwr_off"):
            res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
                body_profile=p362.BODY_MODEL_FX3,
                fw_version=p362.FW_VER_702,
                operation=op,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.dormant_feature_mask, "VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD")
            self.assertFalse(res.anti_dust_menu_exposed)
            self.assertFalse(res.shutter_when_pwr_off_exposed)
            self.assertEqual(res.curtain_state_at_power_off, "OPEN")
            self.assertEqual(res.curtain_closed_at_power_off_events, 0)

    def test_19_81a_fx3_requested_curtain_close_on_power_off_blocked(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            body_profile=p362.BODY_MODEL_FX3,
            operation="power_off_curtain_state",
            requested_curtain_close_on_power_off=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.curtain_state_at_power_off, "OPEN")
        self.assertEqual(res.curtain_closed_at_power_off_events, 0)

    def test_20_81a_fx3_auto_cleaning_power_off_runs_piezo_without_closing_curtain(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            body_profile=p362.BODY_MODEL_FX3,
            fw_version=p362.FW_VER_702,
            operation="auto_cleaning_power_off",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.ibis_ultrasonic_shake_executed)
        self.assertEqual(res.curtain_state_at_power_off, "OPEN")
        self.assertEqual(res.curtain_closed_at_power_off_events, 0)

    def test_21_81a_fx3_sensor_cleaning_label_v702_vs_legacy_v101_cleaning_mode(self) -> None:
        r702 = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            fw_version=p362.FW_VER_702, operation="sensor_cleaning", battery_pct=51
        )
        r101 = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            fw_version=p362.FW_VER_101, operation="sensor_cleaning", battery_pct=51
        )
        self.assertEqual(r702.sensor_cleaning_menu_label, "Sensor Cleaning")
        self.assertEqual(r101.sensor_cleaning_menu_label, "Cleaning Mode")
        self.assertTrue(r702.admitted)
        self.assertTrue(r101.admitted)

    def test_22_81a_fx3_sensor_cleaning_missing_battery_refused_eio(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            operation="sensor_cleaning",
            battery_pct=80,
            np_fz100_inserted=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EIO_ERRNO)
        self.assertFalse(res.ibis_ultrasonic_shake_executed)

    def test_23_81a_fx3_sensor_cleaning_below_51pct_refused_eagain(self) -> None:
        for pct in (0, 25, 50):
            res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
                operation="sensor_cleaning", battery_pct=pct, np_fz100_inserted=True
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EAGAIN_ERRNO)
            self.assertFalse(res.ibis_ultrasonic_shake_executed)
            self.assertFalse(res.mandatory_physical_power_off_prompt)

    def test_24_81a_fx3_sensor_cleaning_at_least_51pct_admitted_with_poweroff_prompt(self) -> None:
        for pct in (51, 75, 100):
            res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
                operation="sensor_cleaning", battery_pct=pct, np_fz100_inserted=True
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.errno_code, 0)
            self.assertTrue(res.ibis_ultrasonic_shake_executed)
            self.assertTrue(res.mandatory_physical_power_off_prompt)
            self.assertEqual(res.curtain_state_at_power_off, "OPEN")

    def test_25_81a_fx6_sealed_end_and_apr_active(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            body_profile=p362.BODY_MODEL_FX6,
            fw_version=p362.FW_VER_601,
            operation="fx6_end_seal_and_apr",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.curtain_state_at_power_off, "NONE_SEALED_END")
        self.assertFalse(res.mechanical_shutter_present)
        self.assertTrue(res.cmos_sealed_behind_end_ircut)
        self.assertEqual(res.variable_nd_range, "1/4..1/128 + CLEAR")
        self.assertTrue(res.apr_calibration_supported)
        self.assertFalse(res.ibis_ultrasonic_shake_executed)

    def test_26_81a_fx6_rejects_shutter_pwroff_and_ibis_sensor_cleaning(self) -> None:
        for op in (
            "anti_dust_function",
            "shutter_when_pwr_off",
            "power_off_curtain_state",
            "auto_cleaning_power_off",
            "sensor_cleaning",
        ):
            res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
                body_profile=p362.BODY_MODEL_FX6,
                fw_version=p362.FW_VER_601,
                operation=op,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.mechanical_shutter_present)
            self.assertTrue(res.cmos_sealed_behind_end_ircut)

    def test_27_81a_all_fx3_versions_keep_curtain_open_and_mask_antidust(self) -> None:
        for fw in (p362.FW_VER_101, p362.FW_VER_200, p362.FW_VER_400, p362.FW_VER_700, p362.FW_VER_702):
            res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
                fw_version=fw, operation="anti_dust_function"
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
            self.assertEqual(res.curtain_state_at_power_off, "OPEN")

    def test_28_81a_invalid_arguments_raise_stage81_error(self) -> None:
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_antidust_shutteropen_and_cleaning_hil(body_profile="FX9")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_antidust_shutteropen_and_cleaning_hil(fw_version="99.00")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_antidust_shutteropen_and_cleaning_hil(operation="close_curtain_hack")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_antidust_shutteropen_and_cleaning_hil(battery_pct=-1)
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_antidust_shutteropen_and_cleaning_hil(battery_pct=101)

    def test_29_81a_pillar_a_passed_in_full_report(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        pa = rep["pillar_a_antidust_shutteropen_sensorcleaning_vs_fx6_end_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["fx3_power_off_curtain_always_open"]["curtain_state_at_power_off"], "OPEN")
        self.assertEqual(pa["fx3_sensor_cleaning_50pct_refused"]["errno_code"], p362.EAGAIN_ERRNO)
        self.assertTrue(pa["fx3_sensor_cleaning_51pct_admitted"]["mandatory_physical_power_off_prompt"])

    def test_30_81a_redlines_match_constants(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertEqual(red["fx3_ilc2210_shutter_when_pwr_off_hits"], 0)
        self.assertEqual(red["fx3_shutter_curtain_at_power_off"], "OPEN")
        self.assertEqual(red["fx3_curtain_closed_at_power_off_events"], 0)
        self.assertEqual(red["fx3_sensor_cleaning_min_battery_pct"], 51)
        self.assertEqual(red["fx3_sensor_cleaning_low_batt_bypass_events"], 0)
        self.assertEqual(red["fx6_shutter_when_power_off_appfw_symbols"], 0)
        self.assertFalse(red["fx6_mechanical_shutter_present"])
        self.assertFalse(red["fx6_ibis_cleaning_supported"])
        self.assertTrue(red["fx6_cmos_sealed_behind_end_ircut"])

    def test_31_81a_compact_donors_verify_sensor_cleaning_and_fx6_apr_tokens(self) -> None:
        s_f = next(d for d in p362.PHASE362_COMPACT_DONORS if d.name == "fx3_string_ja_f")
        self.assertTrue(any("アンチダスト".encode("utf-8") in t for t in s_f.required_tokens))
        s_fx6 = next(d for d in p362.PHASE362_COMPACT_DONORS if d.name == "fx6_string_en")
        self.assertIn(b"APR", s_fx6.required_tokens)

    def test_32_81a_window_donors_verify_fx3_dormant_and_fx6_absent_barrier(self) -> None:
        fx3_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx3_appfw")
        self.assertTrue(any(tok == b"PID_SET_IMAGE_SENSOR_BARRIER" for _, _, tok in fx3_app.windows))
        fx6_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx6_appfw")
        self.assertTrue(any(b"shutter_when_power_off" in f for _, _, f in fx6_app.absent_windows))

    def test_33_81a_fx3_power_off_curtain_state_requires_no_sensor_cleaning_prompt(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(operation="power_off_curtain_state")
        self.assertFalse(res.mandatory_physical_power_off_prompt)
        self.assertFalse(res.ibis_ultrasonic_shake_executed)

    def test_34_81a_fx3_sensor_cleaning_boundary_50_vs_51(self) -> None:
        r50 = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            operation="sensor_cleaning", battery_pct=50
        )
        r51 = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            operation="sensor_cleaning", battery_pct=51
        )
        self.assertFalse(r50.admitted)
        self.assertTrue(r51.admitted)

    def test_35_81a_fx6_still_sealed_end_across_fx6_profile(self) -> None:
        res = p362.simulate_antidust_shutteropen_and_cleaning_hil(
            body_profile=p362.BODY_MODEL_FX6,
            fw_version=p362.FW_VER_601,
            operation="fx6_end_seal_and_apr",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.cmos_sealed_behind_end_ircut)

    # -----------------------------------------------------------------------
    # 36..57: Sub-Model 81B — [Focus Magnifier] 5-Item Cluster, 12.1MP Ratios,
    #         REC Continuity, Clean-HDMI vs FX6 VF x3/x6 & HDMI x2/x4
    # -----------------------------------------------------------------------

    def test_36_81b_fx3_exact_5_item_focus_assistant_cluster_and_c5_binding(self) -> None:
        self.assertEqual(p362.FX3_FOCUS_ASSISTANT_ITEMS_COUNT, 5)
        self.assertEqual(len(p362.FX3_FOCUS_ASSISTANT_5_ITEMS), 5)
        res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie", requested_ratio="x4.0", af_mode="MF", touch_operation="On"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.focus_assistant_items_count, 5)
        self.assertIn("Custom Button 5", res.default_button_binding)
        self.assertTrue(res.mf_double_tap_supported)

    def test_37_81b_fx3_still_ff_exact_ratios_x1_x21_x41(self) -> None:
        self.assertEqual(p362.FX3_STILL_FF_RATIOS, ("x1.0", "x2.1", "x4.1"))
        for r in p362.FX3_STILL_FF_RATIOS:
            res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                shoot_mode="Still_FF", requested_ratio=r
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_ratio, r)
            self.assertEqual(res.allowed_ratios, ("x1.0", "x2.1", "x4.1"))

    def test_38_81b_fx3_still_apsc_exact_ratios_x1_x15_x30(self) -> None:
        self.assertEqual(p362.FX3_STILL_APSC_RATIOS, ("x1.0", "x1.5", "x3.0"))
        for r in p362.FX3_STILL_APSC_RATIOS:
            res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                shoot_mode="Still_APSC", requested_ratio=r
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_ratio, r)

    def test_39_81b_fx3_movie_and_sq_exact_ratios_x1_x40(self) -> None:
        self.assertEqual(p362.FX3_MOVIE_RATIOS, ("x1.0", "x4.0"))
        for sm in ("Movie", "S&Q"):
            for r in p362.FX3_MOVIE_RATIOS:
                res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                    shoot_mode=sm, requested_ratio=r
                )
                self.assertTrue(res.admitted)
                self.assertEqual(res.effective_ratio, r)

    def test_40_81b_fx3_dormant_high_mp_ratios_rejected_eopnotsupp(self) -> None:
        for ratio in p362.FX3_DORMANT_HIGH_MP_RATIOS:
            res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                shoot_mode="Still_FF", requested_ratio=ratio
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_41_81b_fx3_cross_mode_ratios_rejected_eopnotsupp(self) -> None:
        # Movie rejects Still FF x2.1 / x4.1; Still FF rejects Movie x4.0
        r1 = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie", requested_ratio="x2.1"
        )
        r2 = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Still_FF", requested_ratio="x4.0"
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p362.EOPNOTSUPP_ERRNO)
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_42_81b_fx3_v200_to_v702_all_5_items_reset_resistant(self) -> None:
        for fw in (p362.FW_VER_200, p362.FW_VER_400, p362.FW_VER_700, p362.FW_VER_702):
            for op in (
                "focus_magnifier",
                "focus_mag_time",
                "initial_focus_mag",
                "af_in_focus_mag",
                "auto_magnifier_in_mf",
            ):
                res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                    fw_version=fw,
                    operation=op,
                    shoot_mode="Still_FF",
                    requested_ratio="x2.1",
                    af_mode="MF",
                    camera_settings_reset_applied=True,
                )
                self.assertTrue(res.admitted)
                self.assertFalse(res.resettable_via_camera_settings_reset)
                self.assertEqual(res.effective_ratio, "x2.1")

    def test_43_81b_fx3_v101_legacy_focus_magnifier_was_resettable(self) -> None:
        r1 = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            fw_version=p362.FW_VER_101,
            operation="focus_magnifier",
            shoot_mode="Still_FF",
            requested_ratio="x4.1",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r1.resettable_via_camera_settings_reset)
        self.assertEqual(r1.effective_ratio, "x1.0")

    def test_44_81b_fx3_initialize_clears_ratio_and_time(self) -> None:
        res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            fw_version=p362.FW_VER_702,
            operation="initial_focus_mag",
            shoot_mode="Movie",
            requested_ratio="x4.0",
            focus_mag_time="2 Sec",
            initialize_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_ratio, "x1.0")
        self.assertEqual(res.effective_mag_time, "No Limit")

    def test_45_81b_fx3_focus_mag_times_2sec_5sec_no_limit(self) -> None:
        for tm in ("2 Sec", "5 Sec", "No Limit"):
            res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                operation="focus_mag_time", focus_mag_time=tm
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_mag_time, tm)

    def test_46_81b_fx3_af_in_focus_mag_still_only_and_blocked_under_movie_afc_cont_adapter(self) -> None:
        ok = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            operation="af_in_focus_mag", shoot_mode="Still_FF", af_mode="AF-S"
        )
        self.assertTrue(ok.admitted)
        for kwargs in (
            dict(shoot_mode="Movie", af_mode="AF-S"),
            dict(shoot_mode="S&Q", af_mode="AF-S"),
            dict(shoot_mode="Still_FF", af_mode="AF-C"),
            dict(shoot_mode="Still_FF", af_mode="AF-S", cont_shooting=True),
            dict(shoot_mode="Still_FF", af_mode="AF-S", mount_adapter=True),
        ):
            blk = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                operation="af_in_focus_mag", **kwargs
            )
            self.assertFalse(blk.admitted)
            self.assertEqual(blk.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_47_81b_fx3_auto_magnifier_in_mf_still_mf_dmf_only(self) -> None:
        for afm in ("MF", "DMF"):
            ok = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                operation="auto_magnifier_in_mf", shoot_mode="Still_FF", af_mode=afm
            )
            self.assertTrue(ok.admitted)
        for kwargs in (
            dict(shoot_mode="Movie", af_mode="MF"),
            dict(shoot_mode="S&Q", af_mode="MF"),
            dict(shoot_mode="Still_FF", af_mode="AF-S"),
            dict(shoot_mode="Still_FF", af_mode="MF", mount_adapter=True),
        ):
            blk = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
                operation="auto_magnifier_in_mf", **kwargs
            )
            self.assertFalse(blk.admitted)
            self.assertEqual(blk.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_48_81b_fx3_movie_rec_continuity_zero_xavc_crop_and_clean_hdmi(self) -> None:
        res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie",
            requested_ratio="x4.0",
            rec_active=True,
            hdmi_info_display="Off",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.rec_active)
        self.assertTrue(res.rec_continuity_preserved)
        self.assertEqual(res.internal_xavc_cropped_pixels, 0)
        self.assertEqual(res.clean_hdmi_cropped_pixels, 0)
        self.assertFalse(res.hdmi_mirrors_magnifier_osd)

    def test_49_81b_fx3_hdmi_info_display_on_mirrors_osd_without_cropping(self) -> None:
        res = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie",
            requested_ratio="x4.0",
            hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.hdmi_mirrors_magnifier_osd)
        self.assertEqual(res.clean_hdmi_cropped_pixels, 0)

    def test_50_81b_fx3_coexistence_and_suppressions_while_magnified(self) -> None:
        mag = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie", requested_ratio="x4.0"
        )
        unmag = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            shoot_mode="Movie", requested_ratio="x1.0"
        )
        self.assertTrue(mag.coexists_with_peaking_brightmon_desqueeze)
        self.assertTrue(mag.suppresses_marker_vhaf_afilluminator)
        self.assertFalse(unmag.suppresses_marker_vhaf_afilluminator)

    def test_51_81b_fx6_vf_x3_x6_and_hdmi_x2_x4_targets_keep_sdi_mxf_clean(self) -> None:
        vf = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            body_profile=p362.BODY_MODEL_FX6,
            fw_version=p362.FW_VER_601,
            operation="fx6_focus_magnifier",
            fx6_button_target="VF",
            requested_ratio="x6.0",
            rec_active=True,
        )
        hdmi = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            body_profile=p362.BODY_MODEL_FX6,
            fw_version=p362.FW_VER_601,
            operation="fx6_focus_magnifier",
            fx6_button_target="HDMI",
            requested_ratio="x4.0",
            rec_active=True,
        )
        self.assertTrue(vf.admitted)
        self.assertEqual(vf.fx6_target_ratios, ("x3.0", "x6.0"))
        self.assertFalse(vf.hdmi_mirrors_magnifier_osd)
        self.assertTrue(vf.fx6_sdi_and_mxf_never_magnified)
        self.assertTrue(hdmi.admitted)
        self.assertEqual(hdmi.fx6_target_ratios, ("x2.0", "x4.0"))
        self.assertTrue(hdmi.hdmi_mirrors_magnifier_osd)
        self.assertTrue(hdmi.fx6_sdi_and_mxf_never_magnified)

    def test_52_81b_fx6_rejects_fs7_x8_and_fx3_only_af_in_mag(self) -> None:
        r_fs7 = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            body_profile=p362.BODY_MODEL_FX6,
            operation="fx6_focus_magnifier",
            fx6_button_target="VF",
            requested_ratio="x8.0",
        )
        r_af = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            body_profile=p362.BODY_MODEL_FX6,
            operation="af_in_focus_mag",
        )
        self.assertFalse(r_fs7.admitted)
        self.assertEqual(r_fs7.errno_code, p362.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_af.admitted)
        self.assertEqual(r_af.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_53_81b_mf_double_tap_disabled_when_af_or_touch_off(self) -> None:
        r_touch_off = p362.simulate_focus_magnifier_cluster_vs_fx6_hil(
            af_mode="MF", touch_operation="Off"
        )
        self.assertFalse(r_touch_off.mf_double_tap_supported)

    def test_54_81b_invalid_arguments_raise_stage81_error(self) -> None:
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_focus_magnifier_cluster_vs_fx6_hil(shoot_mode="BurstRaw")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_focus_magnifier_cluster_vs_fx6_hil(focus_mag_time="10 Sec")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_focus_magnifier_cluster_vs_fx6_hil(hdmi_info_display="Partial")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_focus_magnifier_cluster_vs_fx6_hil(fx6_button_target="SDI")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_focus_magnifier_cluster_vs_fx6_hil(operation="focus_map")

    def test_55_81b_pillar_b_passed_in_full_report(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        pb = rep["pillar_b_focus_magnifier_cluster_ratios_rec_cleanhdmi_vs_fx6_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["fx3_still_ff_x21"]["effective_ratio"], "x2.1")
        self.assertEqual(pb["fx3_still_apsc_x15"]["effective_ratio"], "x1.5")
        self.assertEqual(pb["fx3_movie_x40_rec_continuity_clean_hdmi"]["clean_hdmi_cropped_pixels"], 0)
        self.assertEqual(pb["fx6_hdmi_x2_x4_target_and_sdi_mxf_clean"]["fx6_target_ratios"], ("x2.0", "x4.0"))

    def test_56_81b_redlines_match_constants(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertEqual(red["fx3_focus_assistant_items_count"], 5)
        self.assertEqual(red["fx3_focus_mag_rec_continuity_broken_events"], 0)
        self.assertEqual(red["fx3_focus_mag_xavc_or_clean_hdmi_crop_pixels"], 0)
        self.assertEqual(red["fx3_dormant_high_mp_mag_ratio_exposed_events"], 0)
        self.assertEqual(red["fx6_sdi_mxf_magnified_events"], 0)

    def test_57_81b_window_donors_verify_fx3_focus_mag_and_fx6_target(self) -> None:
        fx3_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx3_appfw")
        self.assertTrue(any(b"focus_magnification" in tok for _, _, tok in fx3_app.windows))
        fx6_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx6_appfw")
        self.assertTrue(
            any(tok == b"FUNC_monitor_focus_magnifier_x2x4" for _, _, tok in fx6_app.windows)
        )

    # -----------------------------------------------------------------------
    # 58..78: Sub-Model 81C — [Exposure Std. Adjust] 5-Mode +-1 EV 1/6 EV
    #         Reset-Resistant Trap vs FX6 Auto Exposure Level -3.0..+3.0
    # -----------------------------------------------------------------------

    def test_58_81c_fx3_all_5_metering_modes_supported(self) -> None:
        self.assertEqual(p362.FX3_EXP_STD_ADJ_METERING_MODES_COUNT, 5)
        self.assertEqual(
            p362.FX3_METERING_5_MODES,
            ("Multi", "Center", "Spot", "Entire Screen Avg.", "Highlight"),
        )
        for m in p362.FX3_METERING_5_MODES:
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                metering_mode=m, offset_sixths=2
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.metering_mode, m)
            self.assertEqual(res.metering_modes_count, 5)
            self.assertEqual(res.effective_offset_sixths, 2)

    def test_59_81c_fx3_13_steps_minus_6_to_plus_6_in_one_sixth_ev(self) -> None:
        self.assertEqual(p362.FX3_EXP_STD_ADJ_STEPS_PER_MODE, 13)
        for six in range(-6, 7):
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(offset_sixths=six)
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_offset_sixths, six)
            self.assertAlmostEqual(res.effective_offset_ev, six / 6.0, places=5)
            self.assertEqual(res.warning_icon_shown, (six != 0))

    def test_60_81c_fx3_out_of_range_offsets_rejected_einval(self) -> None:
        for bad in (-7, 7, 12):
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(offset_sixths=bad)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EINVAL_ERRNO)

    def test_61_81c_fx3_dormant_step_1_8_rejected_eopnotsupp(self) -> None:
        res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            offset_sixths=2, step_size="1/8"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_62_81c_fx3_reset_resistant_across_camera_settings_reset_cleared_only_by_initialize(self) -> None:
        r_reset = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            metering_mode="Spot",
            offset_sixths=-3,
            camera_settings_reset_applied=True,
        )
        r_init = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            metering_mode="Spot",
            offset_sixths=-3,
            camera_settings_reset_applied=True,
            initialize_applied=True,
        )
        self.assertFalse(r_reset.resettable_via_camera_settings_reset)
        self.assertTrue(r_reset.cleared_only_by_initialize)
        self.assertEqual(r_reset.effective_offset_sixths, -3)
        self.assertTrue(r_reset.warning_icon_shown)
        self.assertEqual(r_init.effective_offset_sixths, 0)
        self.assertFalse(r_init.warning_icon_shown)

    def test_63_81c_fx3_decoupled_from_exposure_comp_and_exif_exposure_bias_value(self) -> None:
        res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            metering_mode="Multi",
            offset_sixths=6,
            exposure_control_mode="P",
            exposure_comp_ev=-0.7,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.exposure_comp_ev, -0.7)
        self.assertEqual(res.exif_exposure_bias_ev, -0.7)
        self.assertAlmostEqual(res.mm_zero_point_shifted_ev, 1.0, places=5)
        self.assertAlmostEqual(res.spot_ael_shifted_ev, 1.0, places=5)
        self.assertAlmostEqual(res.actual_ae_shifted_ev, 1.0, places=5)

    def test_64_81c_fx3_bracket_counter_resets_when_changed_mid_sequence(self) -> None:
        r_brk = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            operation="set_std_adjust",
            offset_sixths=3,
            bracket_in_progress=True,
        )
        r_no_brk = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            operation="set_std_adjust",
            offset_sixths=3,
            bracket_in_progress=False,
        )
        self.assertTrue(r_brk.bracket_counter_reset)
        self.assertFalse(r_no_brk.bracket_counter_reset)

    def test_65_81c_fx3_pas_and_flexible_iso_auto_shift_actual_ae(self) -> None:
        for mode in ("P", "A", "S", "Flexible_ISO_AUTO"):
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                exposure_control_mode=mode, offset_sixths=-4
            )
            self.assertFalse(res.mm_only_affected)
            self.assertAlmostEqual(res.actual_ae_shifted_ev, -4 / 6.0, places=5)

    def test_66_81c_fx3_cine_ei_cine_ei_quick_and_m_fixed_shift_mm_only(self) -> None:
        for mode in ("M_FIXED_ISO", "Cine_EI", "Cine_EI_Quick"):
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                exposure_control_mode=mode, offset_sixths=5
            )
            self.assertTrue(res.mm_only_affected)
            self.assertEqual(res.actual_ae_shifted_ev, 0.0)
            self.assertAlmostEqual(res.mm_zero_point_shifted_ev, 5 / 6.0, places=5)

    def test_67_81c_fx6_auto_exposure_level_25_steps_minus_3_to_plus_3_disproves_2ev_rumor(self) -> None:
        self.assertEqual(p362.FX6_AE_LEVEL_MIN, -3.0)
        self.assertEqual(p362.FX6_AE_LEVEL_MAX, 3.0)
        self.assertEqual(p362.FX6_AE_LEVEL_STEP, 0.25)
        self.assertEqual(p362.FX6_AE_LEVEL_STEPS_COUNT, 25)
        self.assertTrue(p362.FX6_PM_2EV_RUMOR_DISPROVED)
        for i in range(25):
            lvl = -3.0 + 0.25 * i
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                body_profile=p362.BODY_MODEL_FX6,
                fw_version=p362.FW_VER_601,
                operation="fx6_auto_exposure",
                fx6_ae_level=lvl,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.fx6_ae_level, lvl)
            self.assertEqual(res.fx6_ae_level_steps_count, 25)

    def test_68_81c_fx6_rejects_out_of_range_or_non_025_ev_step(self) -> None:
        for bad in (-3.25, 3.25, 0.1, -1.3):
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                body_profile=p362.BODY_MODEL_FX6,
                operation="fx6_auto_exposure",
                fx6_ae_level=bad,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EINVAL_ERRNO)

    def test_69_81c_fx6_ae_speed_range_minus_99_to_plus_99_and_bounds(self) -> None:
        for spd in (-99, 0, 99):
            ok = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                body_profile=p362.BODY_MODEL_FX6,
                operation="fx6_auto_exposure",
                fx6_ae_speed=spd,
            )
            self.assertTrue(ok.admitted)
            self.assertEqual(ok.fx6_ae_speed, spd)
        for bad in (-100, 100):
            blk = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                body_profile=p362.BODY_MODEL_FX6,
                operation="fx6_auto_exposure",
                fx6_ae_speed=bad,
            )
            self.assertFalse(blk.admitted)
            self.assertEqual(blk.errno_code, p362.EINVAL_ERRNO)

    def test_70_81c_fx6_base_look_ae_level_offset_additive_and_modes(self) -> None:
        for mode in p362.VALID_FX6_AE_MODES:
            res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
                body_profile=p362.BODY_MODEL_FX6,
                operation="fx6_auto_exposure",
                fx6_ae_level=1.5,
                fx6_base_look_ae_offset=-0.75,
                fx6_ae_mode=mode,
            )
            self.assertTrue(res.admitted)
            self.assertAlmostEqual(res.actual_ae_shifted_ev, 0.75, places=4)

    def test_71_81c_fx6_cine_ei_locks_agc_and_auto_shutter(self) -> None:
        res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            body_profile=p362.BODY_MODEL_FX6,
            operation="fx6_auto_exposure",
            fx6_cine_ei_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.fx6_agc_and_autoshutter_locked_in_cine_ei)

    def test_72_81c_warning_icon_hidden_at_zero_offset(self) -> None:
        res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(offset_sixths=0)
        self.assertTrue(res.admitted)
        self.assertFalse(res.warning_icon_shown)

    def test_73_81c_invalid_arguments_raise_stage81_error(self) -> None:
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(metering_mode="Matrix3D")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(step_size="1/3")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(exposure_control_mode="AUTO+")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(fx6_ae_mode="SuperFast")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(operation="bad_op")

    def test_74_81c_pillar_c_passed_in_full_report(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        pc = rep["pillar_c_exposure_std_adjust_5mode_reset_trap_vs_fx6_ae_hil"]
        self.assertTrue(pc["passed"])
        self.assertEqual(pc["fx3_spot_reset_resistant_and_exif_decoupled"]["effective_offset_sixths"], -3)
        self.assertEqual(pc["fx3_initialize_clears_std_adjust"]["effective_offset_sixths"], 0)
        self.assertTrue(pc["fx3_cine_ei_mm_only_readout_shifted"]["mm_only_affected"])
        self.assertEqual(pc["fx6_ae_level_minus_3_0_25step_and_base_look"]["fx6_ae_level"], -3.0)

    def test_75_81c_redlines_match_constants(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertEqual(red["fx3_exp_std_adj_metering_modes_count"], 5)
        self.assertEqual(red["fx3_exp_std_adj_steps_per_mode"], 13)
        self.assertEqual(red["fx3_exp_std_adj_step_ev"], "1/6")
        self.assertEqual(red["fx3_exp_std_adj_camera_reset_wipe_events"], 0)
        self.assertEqual(red["fx3_exp_std_adj_exif_bias_mutation_events"], 0)
        self.assertEqual(red["fx3_exp_std_adj_step_1_8_exposed_events"], 0)
        self.assertEqual(red["fx6_ae_level_steps_count"], 25)
        self.assertTrue(red["fx6_pm_2ev_rumor_disproved"])

    def test_76_81c_compact_and_window_donors_cover_exp_std_adj_and_fx6_ae(self) -> None:
        fx6_en = next(d for d in p362.PHASE362_COMPACT_DONORS if d.name == "fx6_string_en")
        self.assertIn(b"Auto Exposure", fx6_en.required_tokens)
        self.assertIn(b"AE Level Offset", fx6_en.required_tokens)
        fx6_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx6_appfw")
        self.assertTrue(
            any(b"BKID_APP_EXTERN_AE_SPEED" in tok for _, _, tok in fx6_app.windows)
        )
        fx3_app = next(w for w in p362.PHASE362_WINDOW_DONORS if w.name == "fx3_appfw")
        self.assertTrue(
            any(b"EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_8" in tok for _, _, tok in fx3_app.windows)
        )

    def test_77_81c_fx6_ae_level_zero_and_positive_three_boundaries(self) -> None:
        r0 = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            body_profile=p362.BODY_MODEL_FX6, operation="fx6_auto_exposure", fx6_ae_level=0.0
        )
        r3 = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            body_profile=p362.BODY_MODEL_FX6, operation="fx6_auto_exposure", fx6_ae_level=3.0
        )
        self.assertTrue(r0.admitted)
        self.assertTrue(r3.admitted)

    def test_78_81c_fx3_initialize_in_pas_also_resets_actual_ae_shift_to_zero(self) -> None:
        res = p362.simulate_exposure_std_adjust_vs_fx6_ae_hil(
            exposure_control_mode="A", offset_sixths=4, initialize_applied=True
        )
        self.assertEqual(res.actual_ae_shifted_ev, 0.0)
        self.assertEqual(res.mm_zero_point_shifted_ev, 0.0)

    # -----------------------------------------------------------------------
    # 79..95: Sub-Model 81D — Wired Smartphone [USB-LAN/Tethering], Zero-RF,
    #         Tier-0 Slot 1 EROFS=30 MSC/MTP Firewall vs FX6 usbg_iap.ko
    # -----------------------------------------------------------------------

    def test_79_81d_fx3_usb_connection_mode_exact_4_items_and_reset_resistant(self) -> None:
        self.assertEqual(p362.FX3_USB_CONNECTION_MODES_COUNT, 4)
        for m in p362.FX3_USB_CONNECTION_4_MODES:
            res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
                operation="usb_connection_mode",
                usb_connection_mode=m,
                camera_settings_reset_applied=True,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.usb_connection_mode, m)

    def test_80_81d_fx3_dormant_usb_streaming_nouvc_rejected_eopnotsupp(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="usb_streaming_nouvc"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_81_81d_fx3_usb_lan_tethering_all_4_drivers_zero_rf_airplane_on(self) -> None:
        self.assertEqual(
            p362.VALID_USB_TETHER_DRIVERS,
            ("cdc_ncm.ko", "cdc_ether.ko", "rndis_host.ko", "ipheth.ko"),
        )
        for op in ("usb_lan_tethering_streaming", "usb_lan_tethering_ftp"):
            for drv in p362.VALID_USB_TETHER_DRIVERS:
                res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
                    operation=op,
                    tethering_driver=drv,
                    airplane_mode="On",
                    usb_lan_cnct_launch="On",
                )
                self.assertTrue(res.admitted)
                self.assertTrue(res.dhcpcd_active)
                self.assertEqual(res.rf_tx_packets, 0)
                self.assertTrue(res.zero_rf_tethering_active)
                self.assertFalse(res.usbg_iap_linked)

    def test_82_81d_fx3_creators_app_usb_streaming_wizard_blocked(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="creators_app_usb", airplane_mode="On"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.creators_app_usb_streaming_wizard_blocked)

    def test_83_81d_fx3_monitor_and_control_usb_disables_tc_focusmap_lut(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="monitor_and_control_usb", airplane_mode="On"
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.mc_usb_timecode_supported)
        self.assertFalse(res.mc_usb_focus_map_supported)
        self.assertFalse(res.mc_usb_lut_import_supported)

    def test_84_81d_fx3_dual_usb_simultaneous_comms_blocked_ebusy(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="dual_usb_ports"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EBUSY_ERRNO)
        self.assertTrue(res.dual_usb_comms_blocked)

    def test_85_81d_fx3_reset_network_set_requires_immediate_airplane_rearm(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="reset_network_set", airplane_mode="On", usb_lan_cnct_launch="On"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.airplane_mode, "Off")
        self.assertEqual(res.usb_lan_cnct_launch, "Off")
        self.assertTrue(res.post_reset_network_airplane_rearm_required)
        self.assertEqual(res.rf_tx_packets, 0)

    def test_86_81d_fx3_slot1_mtp_and_msc_writes_blocked_erofs_30(self) -> None:
        for op in ("mtp_slot_access", "msc_slot_access"):
            res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
                operation=op,
                target_slot="Slot 1",
                host_write_requested=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p362.EROFS_ERRNO)
            self.assertEqual(res.slot1_sector_writes, 0)
            self.assertTrue(res.slot1_erofs_enforced)

    def test_87_81d_fx3_mtp_hard_locks_to_slot1_rejecting_slot2_eopnotsupp(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="mtp_slot_access",
            target_slot="Slot 2",
            host_write_requested=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.target_slot, "Slot 1")

    def test_88_81d_fx3_msc_single_lun_hides_slot2_vs_multi_lun_allows_slot2_read(self) -> None:
        r_single = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="msc_slot_access",
            usb_lun_setting="Single",
            target_slot="Slot 2",
            host_write_requested=False,
        )
        r_multi = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            operation="msc_slot_access",
            usb_lun_setting="Multi",
            target_slot="Slot 2",
            host_write_requested=False,
        )
        self.assertFalse(r_single.admitted)
        self.assertEqual(r_single.errno_code, p362.ENODEV_ERRNO)
        self.assertTrue(r_multi.admitted)
        self.assertEqual(r_multi.slot1_sector_writes, 0)

    def test_89_81d_fx6_usb_tethering_links_usbg_iap_ko_and_forbids_hub(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            body_profile=p362.BODY_MODEL_FX6,
            fw_version=p362.FW_VER_601,
            operation="fx6_usb_tethering_iap",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.tethering_driver, "usbg_iap.ko")
        self.assertTrue(res.usbg_iap_linked)
        self.assertTrue(res.mc_usb_timecode_supported)
        self.assertFalse(res.fx6_usb_hub_allowed)

    def test_90_81d_fx6_rejects_fx3_usb_modes(self) -> None:
        res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
            body_profile=p362.BODY_MODEL_FX6,
            operation="usb_lan_tethering_streaming",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p362.EOPNOTSUPP_ERRNO)

    def test_91_81d_invalid_arguments_raise_stage81_error(self) -> None:
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(operation="usb_host_crack")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(usb_connection_mode="USB Streaming")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(tethering_driver="e1000e.ko")
        with self.assertRaises(p362.Stage81Phase362Error):
            p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(target_slot="Slot 3")

    def test_92_81d_pillar_d_passed_in_full_report(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        pd = rep["pillar_d_usb_tethering_zero_rf_slot1_erofs_vs_fx6_iap_hil"]
        self.assertTrue(pd["passed"])
        self.assertTrue(pd["fx3_cdc_ncm_zero_rf_streaming"]["zero_rf_tethering_active"])
        self.assertEqual(pd["fx3_slot1_mtp_write_erofs_30"]["errno_code"], p362.EROFS_ERRNO)
        self.assertTrue(pd["fx6_usbg_iap_usb_tethering"]["usbg_iap_linked"])

    def test_93_81d_redlines_match_constants(self) -> None:
        rep = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertEqual(red["fx3_usb_connection_modes_count"], 4)
        self.assertTrue(red["fx3_usb_tethering_zero_rf_supported"])
        self.assertEqual(red["fx3_slot1_mtp_msc_write_bypass_events"], 0)
        self.assertEqual(red["fx3_dual_usb_port_simultaneous_events"], 0)
        self.assertEqual(red["fx3_libinfrausbcmn_iap_symbol_count"], 0)
        self.assertTrue(red["fx6_libinfrausbcmn_iap_linked"])

    def test_94_81d_compact_and_window_donors_verify_tethering_and_iap_asymmetry(self) -> None:
        fx3_usb = next(d for d in p362.PHASE362_COMPACT_DONORS if d.name == "fx3_libinfrausbcmn")
        fx6_usb = next(d for d in p362.PHASE362_COMPACT_DONORS if d.name == "fx6_libinfrausbcmn")
        self.assertIn(b"CUsbGadgetIAP", fx3_usb.absent_tokens)
        self.assertIn(b"/usr/kmod/usbg_iap.ko", fx6_usb.required_tokens)

    def test_95_81d_fx3_read_only_slot1_mtp_msc_ok_zero_writes(self) -> None:
        for op in ("mtp_slot_access", "msc_slot_access"):
            res = p362.simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
                operation=op, target_slot="Slot 1", host_write_requested=False
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.slot1_sector_writes, 0)

    # -----------------------------------------------------------------------
    # 96..100: Determinism, CLI, Portability, Suite Integration & Tamper
    # -----------------------------------------------------------------------

    def test_96_normal_vs_clean_room_digests_distinguishable_when_donors_present(self) -> None:
        root = p362.resolve_mac_work_root()
        if IS_CI or p362.is_forced_clean_room() or root is None or (not root.exists()):
            self.skipTest("Donors unavailable or clean-room forced")
        r_loc = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=False
        )
        r_cr = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
            force_clean_room=True
        )
        self.assertNotEqual(r_loc["audit_digest_sha256"], r_cr["audit_digest_sha256"])

    def test_97_standalone_cli_help_summary_and_json_modes(self) -> None:
        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p362.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("81/81", buf_help.getvalue())

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p362.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("Phase 362 Stage 81 (81/81 Stages)", buf_sum.getvalue())
        self.assertIn("curtain=OPEN", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p362.main(["--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "81/81")
        self.assertTrue(parsed["all_checks_passed"])

    def test_98_portability_no_hardcoded_system_python_path_in_module_or_tests(self) -> None:
        forbidden = "/usr/bin/" + "python"
        for path in (Path(p362.__file__).resolve(), Path(__file__).resolve()):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text)
            self.assertIn("sys.dont_write_bytecode = True", text)

    def test_99_suite_default_config_enables_stage81_and_full_run_has_at_least_81_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_stage81)
        self.assertTrue(cfg.include_phase362_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_hil)
        self.assertTrue(cfg.stage81_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_hil)

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s81 = rep["stage81_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_hil"]
        self.assertEqual(s81["milestone"], "81/81")
        self.assertTrue(s81["is_81st_stage_milestone"])

        full_rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(full_rep["all_checks_passed"])
        stage_keys = [k for k in full_rep if k.startswith("stage")]
        self.assertGreaterEqual(len(stage_keys), 81)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_hil=", buf.getvalue())
        self.assertIn("m81=81/81", buf.getvalue())

        buf_skip = io.StringIO()
        with contextlib.redirect_stdout(buf_skip):
            rc2 = suite.main([*_FAST_CLI_FLAGS, "--skip-stage81", "--json"])
        self.assertEqual(rc2, 0)
        rep_skip = json.loads(buf_skip.getvalue())
        self.assertNotIn(
            "stage81_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_hil",
            rep_skip,
        )

        # CLI subprocess execution check (PYTHONPATH + -B)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", str(Path(p362.__file__).resolve()), "--clean-room", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Phase 362 Stage 81 (81/81 Stages)", proc.stdout)

        # Tamper detection on milestone probe fails suite check if mutated
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        with unittest.mock.patch.object(
            p362,
            "run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation",
            wraps=p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation,
        ) as m_run:
            real = p362.run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
                force_clean_room=True
            )
            bad = dict(real)
            bad["milestone"] = "80/80"
            m_run.return_value = bad
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
