"""Dual-mode unit tests (100 cases) for Phase 342 (`preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether`):
19th Real-Hardware Physical Bench Readiness Verifier across Global Sony Waves 70-71 check groups (`A..D`)
covering Reset-immune `Shooting -> [Focus] -> [Peaking Display]` (`Off/On`, `High/Mid/Low`,
`Red/Yellow/Blue/White`, 0 px over HDMI regardless of `HDMI Info. Display`, coexists with `Focus Magnifier`,
Movie AF active, body-dormant `Focus Map` `EOPNOTSUPP=95` wireless *Monitor & Control* only) vs Debunking
FX6 `Peaking Type/Freq` myth (`0` hits in FX6 `appFw.so`, `B&W/Red/Yellow/Blue` only), Ver. 2.00+ Removal
of standalone `[Audio Level Display]` (`0x7a36`) leaving exact 5 Resettable `[Audio Recording]` items &
Debunking FX3 `[Wind Noise Reduct.]` `Auto` myth (`On/Off` only on internal stereo mic, bypassed under
`3.5mm`/`XLR-H1`/`MI Shoe`), `[USB Power Supply]` (`9V/3A` `27W+` Type-C PD, mandatory `NP-FZ100` insertion
law via `libUsbBusPower.so`, zero charging while `ON`, `DC-C1` `>= 65W + 5A`) vs `FX6` `19.5V` `DC IN`
battery-less boot (no hot-replug during `REC`), `[NTSC/PAL Selector]` (`J1` lock vs `CE/E33` `"Running on NTSC."`
vs `U2` `"Running on PAL."`, pure XAVC `AVF_INFO Create?` without mandatory format, Slot-1 `EROFS=30` vs FX6
`System Frequency` `Thumbnail` filter), Dormant `[Anti-Dust Function]`/`[Shutter When Pwr OFF]` myth-busting
(`0` hits in `ilc/2210`, `ALCIN_UUD` mask, mechanical shutter parks `OPEN`, `[Sensor Cleaning]` `>= 51%` IBIS
shake) vs FX6 sealed `e-ND` + `APR`, Reset-immune `[Focus Assistant]` (FF `x1.0->x2.1->x4.1`, APS-C
`x1.0->x1.5->x3.0`, Movie `x1.0<->x4.0`, Still-only AF/Auto Mag, Movie `REC` persistence & Clean-HDMI isolation),
`[Exposure Std. Adjust]` (`-1..+1 EV` in `1/6 EV` across 5 metering modes, Reset-immune trap, 0 EV EXIF
`ExposureBiasValue`) vs Debunking FX6 `±2.0` myth (`-3.0..+3.0` in `0.25` step, 25 steps), wired
`[USB-LAN/Tethering]` (`RTMP/RTMPS/SRT/FTP` under `[Airplane Mode]=On` Zero-RF!) + `usbgmscif_setReadOnly`
& `EROFS=30` Slot-1 MTP/MSC firewall vs FX6 `usbg_iap.ko`, and `16/16 H0 == H3` Dual-Media `528 B FX3RCPT1` Gate.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and donorless CI (`work_root=None`) modes with
zero `.pyc` emission, zero persistent writes, and cross-platform CI headroom.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx6-on-fx3-closure",
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    REQUIRED_H0_BASELINE_KEYS,
    build_default_h0_baselines,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    SIXTEEN_STORAGE_SURFACES,
)
from fx6_closure.realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier import (  # noqa: E402
    P342_ALCIN_UUD_MASK_ENUM,
    P342_AUDIO_REC_LEVEL_DEFAULT,
    P342_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL,
    P342_AUDIO_REC_LEVEL_MAX,
    P342_AUDIO_REC_LEVEL_MIN,
    P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS,
    P342_AVF_INFO_CREATE_PROMPT,
    P342_BOUNDED_DONOR_PATHS,
    P342_CHECK_GROUP_A_ID,
    P342_CHECK_GROUP_B_ID,
    P342_CHECK_GROUP_C_ID,
    P342_CHECK_GROUP_D_ID,
    P342_DC_C1_MIN_CABLE_AMPS,
    P342_DC_C1_MIN_PD_WATTS,
    P342_DORMANT_ANTI_DUST_FUNCTION_RESID16_HEX,
    P342_DORMANT_FOCUS_MAP_RESIDS,
    P342_DORMANT_HIGH_MP_MAG_SCALES,
    P342_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX,
    P342_ERRNO_EBUSY,
    P342_ERRNO_EOPNOTSUPP,
    P342_ERRNO_EROFS,
    P342_EXP_STD_ADJ_EXACT_STEPS,
    P342_EXP_STD_ADJ_FIVE_METERING_MODES,
    P342_EXP_STD_ADJ_MODIFIES_EXIF_BIAS,
    P342_EXP_STD_ADJ_RESET_IMMUNE,
    P342_EXP_STD_ADJ_STEP_ENUM,
    P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS,
    P342_FOCUS_MAG_OUTPUTS_TO_HDMI,
    P342_FOCUS_MAG_PERSISTS_DURING_MOVIE_REC,
    P342_FX3_AUDIO_LEVEL_DISPLAY_MENU_PRESENT,
    P342_FX3_CHARGES_BATTERY_WHILE_ON,
    P342_FX3_CUSB_GADGET_IAP_HITS,
    P342_FX3_ILC2210_SHUTTER_PWROFF_HITS,
    P342_FX3_IN_BODY_FOCUS_MAP_PRESENT,
    P342_FX3_PEAKING_OUTPUTS_TO_HDMI,
    P342_FX3_POWER_OFF_SHUTTER_PARK_STATE,
    P342_FX3_SHUTTER_WHEN_PWR_OFF_PRESENT,
    P342_FX3_SUPPORTS_BATTERYLESS_USB_PD_BOOT,
    P342_FX3_WIND_NOISE_AUTO_PRESENT,
    P342_FX6_AE_LEVEL_EXACT_STEPS,
    P342_FX6_AE_LEVEL_MAX_EV,
    P342_FX6_AE_LEVEL_MIN_EV,
    P342_FX6_AE_LEVEL_STEP_EV,
    P342_FX6_BATTERYLESS_DC_IN_BOOT_SUPPORTED,
    P342_FX6_CUSB_GADGET_IAP_PRESENT,
    P342_FX6_DC_IN_NOMINAL_VOLTS,
    P342_FX6_E_ND_STEPS,
    P342_FX6_HDMI_FOCUS_MAG_SCALES,
    P342_FX6_LIMITER_MODE_SIX_STEPS,
    P342_FX6_PEAKING_EXACT_THREE_ITEMS,
    P342_FX6_PEAKING_FOUR_COLORS,
    P342_FX6_PEAKING_TYPE_FREQ_SYMBOL_HITS,
    P342_FX6_VF_FOCUS_MAG_SCALES,
    P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH,
    P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH,
    P342_GA_ERR_MODEL_OR_FW_FLOOR,
    P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP,
    P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY,
    P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO,
    P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS,
    P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW,
    P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF,
    P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY,
    P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI,
    P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR,
    P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP,
    P342_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH,
    P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP,
    P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX,
    P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE,
    P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
    P342_MOVIE_MAG_CYCLE_SCALES,
    P342_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P342_PEAKING_EXACT_THREE_ITEMS,
    P342_PEAKING_FOUR_COLORS,
    P342_PEAKING_THREE_LEVELS,
    P342_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX,
    P342_RUNNING_ON_NTSC_BANNER,
    P342_RUNNING_ON_PAL_BANNER,
    P342_SCHEMA,
    P342_SENSOR_CLEANING_MIN_BATTERY_PCT,
    P342_SHUTTER_BARRIER_BKID,
    P342_SONY_HELP_GUIDE_ID,
    P342_STILL_APSC_MAG_CYCLE_SCALES,
    P342_STILL_FF_MAG_CYCLE_SCALES,
    P342_STORAGE_SURFACE_COUNT,
    P342_USB_BUS_POWER_REQUIRED_SYMBOLS,
    P342_USB_LAN_KERNEL_MODULES,
    P342_USB_LAN_LIBS,
    P342_USB_PD_RECOMMENDED_WATTS,
    P342_USBGMSCIF_READONLY_SYMBOL,
    P342_VERSION,
    P342_WIND_NOISE_REDUCT_EXACT_TWO_MODES,
    P342_XAVC_REQUIRES_MANDATORY_CARD_FORMAT,
    PHASE342_EMMC_WRITE_COUNT,
    PHASE342_E_ND_ACTUATOR_TX_COUNT,
    PHASE342_PASSIVE_TX_BYTES_EMITTED,
    PHASE342_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE342_SLOT1_DATA_SECTOR_WRITES,
    PHASE342_USB_PACKETS_TRANSMITTED,
    PHASE342_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_342_CHECK_GROUP_IDS,
    PHASE_342_SCHEMA,
    PHASE_342_VERSION,
    _canonical_sha256_dict,
    build_simulated_phase342_tier0_receipts,
    evaluate_p342_check_group_a_peaking_audio_and_wind,
    evaluate_p342_check_group_b_usb_pd_and_ntsc_pal,
    evaluate_p342_check_group_c_antidust_and_focus_assistant,
    evaluate_p342_check_group_d_exp_std_usblan_and_tier0,
    evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight,
    inspect_phase342_donors_bounded,
    render_phase342_markdown,
    resolve_phase342_donor_file_or_none,
    run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight,
    verify_phase342_report,
)


def _run_cli_subprocess(
    args: list[str],
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(REPO_ROOT / p)
        for p in (
            "outputs/fx6-on-fx3-closure",
            "outputs/fx3-safety",
            "outputs/fx3-recovery-adapter",
            "outputs/fx3-firmware-lab",
            "outputs/fx3-vm",
        )
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "fx6_closure",
            "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestPhase342Preflight19Verifier(unittest.TestCase):
    def _assert_err(self, res: object, err_prefix: str) -> None:
        errors = getattr(res, "errors")
        self.assertTrue(
            any(e == err_prefix or e.startswith(f"{err_prefix}:") for e in errors),
            f"Expected error starting with {err_prefix!r} in {errors!r}",
        )

    def _assert_err_contains(self, res: object, token: str) -> None:
        errors = getattr(res, "errors")
        self.assertTrue(
            any(token in e for e in errors),
            f"Expected substring {token!r} in {errors!r}",
        )

    # ------------------------------------------------------------------
    # 01-15: Exports, Schema, Four-Mode Donorless CI & Determinism
    # ------------------------------------------------------------------

    def test_01_package_exports_and_schema_constants(self) -> None:
        self.assertEqual(
            P342_SCHEMA,
            "realhw_preflight19_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether_v1",
        )
        self.assertEqual(PHASE_342_SCHEMA, P342_SCHEMA)
        self.assertEqual(P342_VERSION, "phase342_v1")
        self.assertEqual(PHASE_342_VERSION, "phase342_v1")
        self.assertEqual(P342_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_342_CHECK_GROUP_IDS), 4)
        self.assertTrue(
            hasattr(
                fx6_closure,
                "run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight",
            )
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase342_report"))

    def test_02_default_run_blocks_awaiting_tier0_receipt_with_4_of_4_groups(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True
        )
        self.assertEqual(rep.overall_status, P342_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase342_report(rep).valid)

    def test_03_simulate_bench_dry_run_passes_and_keeps_attach_false(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertTrue(verify_phase342_report(rep).valid)

    def test_04_physical_dual_media_receipt_passes_with_distinct_stdev(self) -> None:
        sim = build_simulated_phase342_tier0_receipts(
            body_serial="FX3REAL70200342",
            emmc_cid="11010030303847333000a1b2c3d47777",
        )
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2001,
            st_dev_b_override=2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertEqual(
            rep.go_no_go,
            P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase342_report(rep).valid)

    def test_05_resolve_phase342_donor_file_or_none_handles_none_work_root(self) -> None:
        for _lbl, rel in P342_BOUNDED_DONOR_PATHS:
            self.assertIsNone(resolve_phase342_donor_file_or_none(None, rel))

    def test_06_four_mode_determinism_and_recursive_elapsed_seconds_stripping(self) -> None:
        rep_clean = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep_cr_env = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep_force_env = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch(
            "fx6_closure.realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_verifier._resolve_work_root_or_none",
            return_value=None,
        ):
            rep_donorless = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
                force_clean_room=False, simulate_bench_dry_run=True
            )
        self.assertEqual(rep_donorless.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(rep_donorless.donor_inspection.donor_tree_present)
        self.assertEqual(rep_clean.report_sha256, rep_cr_env.report_sha256)
        self.assertEqual(rep_clean.report_sha256, rep_force_env.report_sha256)
        self.assertEqual(rep_clean.report_sha256, rep_donorless.report_sha256)
        js = rep_clean.to_deterministic_json()
        self.assertNotIn("elapsed_seconds", js)
        self.assertNotIn("elapsed_ms", js)

    def test_07_canonical_sha256_strips_nested_timing_fields(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d1 = copy.deepcopy(rep.to_dict())
        d2 = copy.deepcopy(rep.to_dict())
        d2["donor_inspection"]["elapsed_seconds"] = 999.999
        d2["check_group_a"]["nested_elapsed_ms"] = 12345
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_08_local_donor_o_rdonly_bounded_inspection_if_present(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            donor = inspect_phase342_donors_bounded(force_clean_room=False)
            self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
            self.assertTrue(donor.within_budget)
            if donor.donor_tree_present:
                self.assertEqual(donor.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertGreater(donor.bytes_read_total, 0)
                self.assertLessEqual(donor.bytes_read_total, 8 * 64)
            else:
                self.assertEqual(donor.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_09_clean_room_mode_zero_leaked_bytes(self) -> None:
        donor = inspect_phase342_donors_bounded(force_clean_room=True)
        self.assertEqual(donor.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(donor.bytes_read_total, 0)
        self.assertEqual(donor.raw_firmware_bytes_leaked, 0)
        self.assertTrue(donor.within_budget)

    def test_10_verify_report_rejects_tampered_sha256(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = rep.to_dict()
        d["report_sha256"] = "0" * 64
        res = verify_phase342_report(d)
        self.assertFalse(res.valid)
        self._assert_err_contains(res, "report_sha256 mismatch")

    def test_11_verify_report_rejects_unlocked_hard_booleans_and_zeros(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        for field in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "cross_model_flash_authorized",
            "fx3_peaking_outputs_to_hdmi",
            "fx3_wind_noise_auto_present",
            "fx3_shutter_when_pwr_off_present",
            "fx3_focus_mag_outputs_to_hdmi",
        ):
            d = rep.to_dict()
            d[field] = True
            self.assertFalse(verify_phase342_report(d).valid)
        for field in (
            "emmc_write_count",
            "e_nd_actuator_tx_count",
            "rf_packets_transmitted",
            "slot1_data_sector_writes",
            "raw_firmware_bytes_leaked",
        ):
            d = rep.to_dict()
            d[field] = 1
            self.assertFalse(verify_phase342_report(d).valid)

    def test_12_verify_report_rejects_wrong_schema_and_help_guide(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True
        )
        d = rep.to_dict()
        d["schema_version"] = "wrong"
        d["sony_help_guide_id"] = "ilc/2110"
        res = verify_phase342_report(d)
        self.assertFalse(res.valid)
        self._assert_err_contains(res, "schema_version mismatch")
        self._assert_err_contains(res, "ilc/2210")

    def test_13_render_markdown_includes_all_four_groups_and_sha(self) -> None:
        rep = run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase342_markdown(rep)
        self.assertIn(P342_CHECK_GROUP_A_ID, md)
        self.assertIn(P342_CHECK_GROUP_B_ID, md)
        self.assertIn(P342_CHECK_GROUP_C_ID, md)
        self.assertIn(P342_CHECK_GROUP_D_ID, md)
        self.assertIn(rep.report_sha256, md)

    def test_14_zero_leaked_firmware_bytes_on_all_hard_constants(self) -> None:
        self.assertEqual(PHASE342_EMMC_WRITE_COUNT, 0)
        self.assertEqual(PHASE342_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(PHASE342_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE342_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE342_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE342_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE342_RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_15_donor_relative_paths_have_non_empty_expected_eight_entries(self) -> None:
        self.assertEqual(len(P342_BOUNDED_DONOR_PATHS), 8)
        labels = [lbl for lbl, _ in P342_BOUNDED_DONOR_PATHS]
        self.assertIn("fx6_appfw_so", labels)
        self.assertIn("fx3_libusbbuspower_so", labels)
        self.assertIn("fx3_libnetservicetethering_so", labels)
        self.assertIn("fx3_libinfrausbcmn_so", labels)

    # ------------------------------------------------------------------
    # 16-36: Check Group A — Peaking Display, Audio Level Removal, Wind Noise
    # ------------------------------------------------------------------

    def test_16_ga_rejects_wrong_model_fw_or_help_guide(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            body_model_id=0x12345678,
            body_fw="6.01",
            sony_help_guide_id="ilc/9999",
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_17_ga_peaking_three_items_levels_and_four_colors(self) -> None:
        self.assertEqual(P342_PEAKING_EXACT_THREE_ITEMS, ("PEAKING_DISPLAY", "PEAKING_LEVEL", "PEAKING_COLOR"))
        self.assertEqual(P342_PEAKING_THREE_LEVELS, ("HIGH", "MID", "LOW"))
        self.assertEqual(P342_PEAKING_FOUR_COLORS, ("RED", "YELLOW", "BLUE", "WHITE"))
        for lvl in P342_PEAKING_THREE_LEVELS:
            for col in P342_PEAKING_FOUR_COLORS:
                ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
                    peaking_display="ON", peaking_level=lvl, peaking_color=col
                )
                self.assertTrue(ga.passed)
                self.assertFalse(ga.fx3_peaking_outputs_to_hdmi)

    def test_18_ga_peaking_rejects_hdmi_output_claim(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            peaking_display="ON",
            hdmi_info_display="ON",
            expect_peaking_outputs_over_hdmi=True,
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP)
        self._assert_err_contains(ga, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_19_ga_peaking_coexists_with_focus_magnifier_and_warns_lcd_only(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            peaking_display="ON", focus_magnifier_active=True
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.peaking_coexists_with_focus_magnifier)
        self.assertTrue(any("Focus Magnifier" in w for w in ga.warnings))

    def test_20_ga_rejects_claimed_peaking_blocks_focus_magnifier(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            claimed_peaking_blocks_focus_magnifier=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP)

    def test_21_ga_rejects_claimed_peaking_disabled_in_movie_af(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            shoot_mode="MOVIE", focus_mode="AF_C", claimed_peaking_disabled_in_movie_af=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP)

    def test_22_ga_rejects_claimed_peaking_wiped_by_camera_reset(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            reset_action="CAMERA_SETTINGS_RESET", claimed_peaking_wiped_by_camera_reset=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP)

    def test_23_ga_rejects_body_dormant_focus_map_and_usb_mc_claim(self) -> None:
        self.assertEqual(P342_DORMANT_FOCUS_MAP_RESIDS, ("0x61f9", "0x6247"))
        self.assertFalse(P342_FX3_IN_BODY_FOCUS_MAP_PRESENT)
        for kw in (
            {"in_body_focus_map_requested": True},
            {"claimed_fx3_has_in_body_focus_map": True},
            {"claimed_mc_focus_map_works_over_usb": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP)
            self._assert_err_contains(ga, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_24_ga_debunks_fx6_peaking_type_freq_myth_and_bw_vs_white(self) -> None:
        self.assertEqual(P342_FX6_PEAKING_TYPE_FREQ_SYMBOL_HITS, 0)
        self.assertEqual(P342_FX6_PEAKING_EXACT_THREE_ITEMS, ("SETTING", "PEAKING_LEVEL", "COLOR"))
        self.assertEqual(P342_FX6_PEAKING_FOUR_COLORS, ("BW", "RED", "YELLOW", "BLUE"))
        for kw in (
            {"fx6_peaking_type_or_freq_requested": True},
            {"claimed_fx6_has_peaking_type_or_freq": True},
            {"claimed_fx6_peaking_has_white_not_bw": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH)

    def test_25_ga_ver200_audio_level_display_removed_0x7a36(self) -> None:
        self.assertEqual(P342_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX, "0x7a36")
        self.assertFalse(P342_FX3_AUDIO_LEVEL_DISPLAY_MENU_PRESENT)
        for kw in (
            {"dormant_audio_level_display_requested": True},
            {"claimed_fx3_has_audio_level_display_menu": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)
            self._assert_err_contains(ga, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_26_ga_audio_recording_exact_five_items_enforced(self) -> None:
        self.assertEqual(len(P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS), 5)
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            exposed_audio_recording_items=(*P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS, "AUDIO_LEVEL_DISPLAY")
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)

    def test_27_ga_audio_rec_level_default_26_and_range_0_31(self) -> None:
        self.assertEqual(P342_AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertEqual(P342_AUDIO_REC_LEVEL_MIN, 0)
        self.assertEqual(P342_AUDIO_REC_LEVEL_MAX, 31)
        self.assertEqual(P342_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL, "adj_audio_rec_level_defult")
        self.assertTrue(evaluate_p342_check_group_a_peaking_audio_and_wind(audio_rec_level=0).passed)
        self.assertTrue(evaluate_p342_check_group_a_peaking_audio_and_wind(audio_rec_level=31).passed)
        ga_bad = evaluate_p342_check_group_a_peaking_audio_and_wind(audio_rec_level=32)
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)

    def test_28_ga_rejects_disable_builtin_limiter_and_fx6_6step_limiter_on_fx3(self) -> None:
        self.assertEqual(len(P342_FX6_LIMITER_MODE_SIX_STEPS), 6)
        for kw in (
            {"fx3_disable_builtin_limiter_requested": True},
            {"claimed_fx3_has_fx6_6step_limiter": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)

    def test_29_ga_rejects_audio_recording_resists_reset_and_wrong_audio_out_timing_path(self) -> None:
        for kw in (
            {"claimed_audio_recording_resists_camera_reset": True},
            {"claimed_audio_out_timing_under_setup_sound_option": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)

    def test_30_ga_debunks_wind_noise_auto_myth(self) -> None:
        self.assertEqual(P342_WIND_NOISE_REDUCT_EXACT_TWO_MODES, ("OFF", "ON"))
        self.assertFalse(P342_FX3_WIND_NOISE_AUTO_PRESENT)
        for kw in (
            {"wind_noise_reduct": "AUTO"},
            {"dormant_wind_noise_auto_requested": True},
            {"claimed_fx3_wind_noise_has_auto": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)
            self._assert_err_contains(ga, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_31_ga_wind_noise_active_only_on_internal_stereo_mic(self) -> None:
        ga_int = evaluate_p342_check_group_a_peaking_audio_and_wind(
            wind_noise_reduct="ON", xlr_h1_attached=False
        )
        self.assertTrue(ga_int.passed)
        self.assertTrue(ga_int.wind_noise_internal_mic_active)

    def test_32_ga_wind_noise_bypassed_under_35mm_xlr_h1_or_mi_shoe(self) -> None:
        for kw in (
            {"mic_35mm_inserted": True},
            {"xlr_h1_attached": True, "xlr_h1_handle_audio": "ON"},
            {"mi_shoe_mic_attached": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(wind_noise_reduct="ON", **kw)
            self.assertTrue(ga.passed)
            self.assertFalse(ga.wind_noise_internal_mic_active)

    def test_33_ga_rejects_wind_noise_applies_to_external_mic_or_sq(self) -> None:
        for kw in (
            {"expect_wind_noise_applies_to_external_mic": True},
            {"expect_wind_noise_active_in_sq": True},
        ):
            ga = evaluate_p342_check_group_a_peaking_audio_and_wind(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)

    def test_34_ga_wind_noise_disabled_in_sq_mode(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            shoot_mode="S_AND_Q", wind_noise_reduct="ON", xlr_h1_attached=False
        )
        self.assertTrue(ga.passed)
        self.assertFalse(ga.wind_noise_internal_mic_active)

    def test_35_ga_rejects_fx6_handle_physical_low_cut_switch_myth(self) -> None:
        ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
            claimed_fx6_handle_has_physical_low_cut_switch=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH)
        self.assertFalse(ga.fx6_handle_physical_low_cut_switch)

    def test_36_ga_audio_out_timing_and_shoe_audio_set_options(self) -> None:
        for timing in ("LIVE", "LIP_SYNC"):
            for shoe in ("48KHZ_24BIT_4CH", "48KHZ_24BIT_2CH", "48KHZ_16BIT_2CH"):
                ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
                    audio_out_timing=timing, shoe_audio_set=shoe
                )
                self.assertTrue(ga.passed)

    # ------------------------------------------------------------------
    # 37-57: Check Group B — USB PD, NP-FZ100 Law, DC-C1, NTSC/PAL, Slot-1 EROFS
    # ------------------------------------------------------------------

    def test_37_gb_usb_pd_9v3a_type_c_with_np_fz100_passes(self) -> None:
        self.assertEqual(P342_USB_PD_RECOMMENDED_WATTS, 27.0)
        self.assertIn("GetCurrentBattState", P342_USB_BUS_POWER_REQUIRED_SYMBOLS)
        self.assertIn("VAL_battery_inserted_BATTERY_IS_INSERTED", P342_USB_BUS_POWER_REQUIRED_SYMBOLS)
        gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            usb_power_supply="ON", usb_pd_watts=27.0, np_fz100_inserted=True, battery_soc_pct=85
        )
        self.assertTrue(gb.passed)
        self.assertFalse(gb.fx3_charges_battery_while_on)
        self.assertFalse(gb.fx3_supports_batteryless_usb_pd_boot)

    def test_38_gb_rejects_multi_micro_usb_power_and_claim(self) -> None:
        for kw in (
            {"usb_power_terminal": "MULTI_MICRO_USB"},
            {"claimed_multi_micro_usb_powers_camera": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW)

    def test_39_gb_enforces_mandatory_np_fz100_insertion_law(self) -> None:
        for kw in (
            {"np_fz100_inserted": False},
            {"battery_soc_pct": 0},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW)
            self._assert_err_contains(gb, "BATTERY_IS_INSERTED")

    def test_40_gb_rejects_sub_27w_usb_pd_while_camera_on(self) -> None:
        gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            camera_power_state="ON", usb_pd_supply_active=True, usb_pd_watts=18.0
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW)

    def test_41_gb_rejects_battery_charging_while_camera_on(self) -> None:
        for kw in (
            {"charge_led_active_while_on": True},
            {"expect_battery_charges_while_camera_on": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(camera_power_state="ON", **kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW)

    def test_42_gb_rejects_batteryless_usb_pd_boot_and_hot_swap_myths(self) -> None:
        for kw in (
            {"claimed_fx3_supports_batteryless_usb_pd_boot": True},
            {"claimed_np_fz100_hot_swap_under_usb_pd": True},
            {"claimed_usb_power_supply_wiped_by_camera_reset": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW)

    def test_43_gb_dc_c1_requires_65w_pd_and_5a_cable(self) -> None:
        self.assertEqual(P342_DC_C1_MIN_PD_WATTS, 65.0)
        self.assertEqual(P342_DC_C1_MIN_CABLE_AMPS, 5)
        self.assertTrue(
            evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
                dc_c1_coupler_attached=True, usb_pd_watts=65.0, usb_c_cable_amps=5
            ).passed
        )
        gb_low_w = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            dc_c1_coupler_attached=True, usb_pd_watts=45.0, usb_c_cable_amps=5
        )
        self.assertFalse(gb_low_w.passed)
        self._assert_err(gb_low_w, P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY)
        gb_3a = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            dc_c1_coupler_attached=True, usb_pd_watts=65.0, usb_c_cable_amps=3
        )
        self.assertFalse(gb_3a.passed)
        self._assert_err(gb_3a, P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY)

    def test_44_gb_fx6_19_5v_dc_in_batteryless_boot_and_hot_replug_hazard(self) -> None:
        self.assertEqual(P342_FX6_DC_IN_NOMINAL_VOLTS, 19.5)
        self.assertTrue(P342_FX6_BATTERYLESS_DC_IN_BOOT_SUPPORTED)
        for kw in (
            {"fx6_dc_in_volts": 12.0},
            {"fx6_dc_in_hot_replug_during_rec": True},
            {"claimed_fx6_usb_c_powers_body": True},
            {"claimed_fx6_lacks_batteryless_dc_in_boot": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY)

    def test_45_gb_ntsc_pal_j1_sku_locked_to_ntsc(self) -> None:
        self.assertTrue(
            evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku="J1", video_system="NTSC").passed
        )
        for kw in (
            {"ntsc_pal_sku": "J1", "video_system": "PAL"},
            {"ntsc_pal_sku": "J1", "video_system": "NTSC", "ntsc_pal_switch_requested": True},
            {"ntsc_pal_sku": "J1", "video_system": "NTSC", "claimed_j1_supports_pal_selector": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO)

    def test_46_gb_ntsc_pal_ce_e33_running_on_ntsc_banner(self) -> None:
        for sku in ("CE", "E33"):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku=sku, video_system="NTSC")
            self.assertTrue(gb.passed)
            self.assertEqual(gb.ntsc_pal_boot_banner, P342_RUNNING_ON_NTSC_BANNER)
            self.assertTrue(any("Running on NTSC." in w for w in gb.warnings))

    def test_47_gb_ntsc_pal_u2_running_on_pal_banner(self) -> None:
        gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku="U2", video_system="PAL")
        self.assertTrue(gb.passed)
        self.assertEqual(gb.ntsc_pal_boot_banner, P342_RUNNING_ON_PAL_BANNER)
        self.assertTrue(any("Running on PAL." in w for w in gb.warnings))

    def test_48_gb_ntsc_pal_default_systems_have_empty_banner(self) -> None:
        self.assertEqual(
            evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku="CE", video_system="PAL").ntsc_pal_boot_banner,
            "",
        )
        self.assertEqual(
            evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku="U2", video_system="NTSC").ntsc_pal_boot_banner,
            "",
        )

    def test_49_gb_ntsc_pal_switch_requires_cold_reboot(self) -> None:
        gb_ok = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            ntsc_pal_switch_requested=True, ntsc_pal_reboot_acknowledged=True
        )
        self.assertTrue(gb_ok.passed)
        gb_bad = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            ntsc_pal_switch_requested=True, ntsc_pal_reboot_acknowledged=False
        )
        self.assertFalse(gb_bad.passed)
        self._assert_err(gb_bad, P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO)

    def test_50_gb_ntsc_pal_rejects_mandatory_format_and_cross_system_myths(self) -> None:
        self.assertFalse(P342_XAVC_REQUIRES_MANDATORY_CARD_FORMAT)
        self.assertIn("Create?", P342_AVF_INFO_CREATE_PROMPT)
        for kw in (
            {"expect_non_default_system_lacks_banner": True},
            {"claimed_xavc_requires_mandatory_card_format": True},
            {"expect_cross_system_playback_allowed": True},
            {"claimed_ntsc_pal_wiped_by_camera_reset": True},
            {"claimed_fx6_shows_running_on_ntsc_pal_banner": True},
            {"claimed_fx6_thumbnail_shows_all_freq_simultaneously": True},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO)

    def test_51_gb_slot1_avf_info_write_blocked_erofs30_slot2_allowed(self) -> None:
        gb_s2 = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            ntsc_pal_avf_info_write_requested=True, ntsc_pal_avf_target_slot=2
        )
        self.assertTrue(gb_s2.passed)
        gb_s1 = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            ntsc_pal_avf_info_write_requested=True, ntsc_pal_avf_target_slot=1, slot1_contains_tier0_dump=True
        )
        self.assertFalse(gb_s1.passed)
        self._assert_err(gb_s1, P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS)
        self._assert_err_contains(gb_s1, f"errno={P342_ERRNO_EROFS}")

    def test_52_gb_slot1_format_and_sector_writes_blocked_erofs30(self) -> None:
        for kw in (
            {"slot1_format_requested": True},
            {"slot1_data_sector_writes": 1},
        ):
            gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(slot1_contains_tier0_dump=True, **kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS)

    def test_53_gb_invalid_sku_or_video_system_rejected(self) -> None:
        self.assertFalse(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(ntsc_pal_sku="US").passed)
        self.assertFalse(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(video_system="SECAM").passed)

    def test_54_gb_camera_off_allows_low_pd_watts_when_np_fz100_present(self) -> None:
        gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            camera_power_state="OFF", usb_pd_watts=15.0, charge_led_active_while_on=True
        )
        self.assertTrue(gb.passed)

    def test_55_gb_invalid_usb_power_supply_or_camera_power_state_rejected(self) -> None:
        self.assertFalse(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(usb_power_supply="AUTO").passed)
        self.assertFalse(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(camera_power_state="SLEEP").passed)

    def test_56_gb_dc_c1_passes_with_100w_and_5a_cable(self) -> None:
        gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
            dc_c1_coupler_attached=True, usb_pd_watts=100.0, usb_c_cable_amps=5
        )
        self.assertTrue(gb.passed)

    def test_57_gb_fx6_dc_in_boundary_18v_and_20_5v(self) -> None:
        self.assertTrue(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(fx6_dc_in_volts=18.0).passed)
        self.assertTrue(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(fx6_dc_in_volts=20.5).passed)
        self.assertFalse(evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(fx6_dc_in_volts=21.0).passed)

    # ------------------------------------------------------------------
    # 58-77: Check Group C — Dormant Anti-Dust/Shutter Pwr OFF & Focus Assistant
    # ------------------------------------------------------------------

    def test_58_gc_rejects_dormant_antidust_and_shutter_when_pwr_off(self) -> None:
        self.assertEqual(P342_DORMANT_ANTI_DUST_FUNCTION_RESID16_HEX, "0x7495")
        self.assertEqual(P342_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX, "0x709f")
        self.assertEqual(P342_SHUTTER_BARRIER_BKID, "BKID_APP_setting_image_sensor_barrier")
        self.assertEqual(P342_ALCIN_UUD_MASK_ENUM, "VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD")
        self.assertFalse(P342_FX3_SHUTTER_WHEN_PWR_OFF_PRESENT)
        self.assertEqual(P342_FX3_ILC2210_SHUTTER_PWROFF_HITS, 0)
        for kw in (
            {"dormant_anti_dust_function_requested": True},
            {"dormant_shutter_when_pwr_off_requested": True},
            {"claimed_fx3_shutter_when_pwr_off_present": True},
        ):
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF)
            self._assert_err_contains(gc, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_59_gc_mechanical_shutter_parks_open_on_power_off(self) -> None:
        self.assertEqual(P342_FX3_POWER_OFF_SHUTTER_PARK_STATE, "OPEN")
        gc_ok = evaluate_p342_check_group_c_antidust_and_focus_assistant()
        self.assertEqual(gc_ok.fx3_power_off_shutter_park_state, "OPEN")
        gc_bad = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            claimed_fx3_shutter_closes_on_power_off=True
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF)

    def test_60_gc_sensor_cleaning_requires_51pct_battery_and_mandatory_off(self) -> None:
        self.assertEqual(P342_SENSOR_CLEANING_MIN_BATTERY_PCT, 51)
        self.assertTrue(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(
                sensor_cleaning_requested=True,
                battery_soc_pct=51,
                sensor_cleaning_power_off_completed=True,
            ).passed
        )
        gc_low = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            sensor_cleaning_requested=True, battery_soc_pct=50, sensor_cleaning_power_off_completed=True
        )
        self.assertFalse(gc_low.passed)
        self._assert_err(gc_low, P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR)
        gc_no_off = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            sensor_cleaning_requested=True, battery_soc_pct=85, sensor_cleaning_power_off_completed=False
        )
        self.assertFalse(gc_no_off.passed)
        self._assert_err(gc_no_off, P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR)

    def test_61_gc_rejects_fx6_ibis_cleaning_or_fx3_e_nd_apr_claims(self) -> None:
        self.assertEqual(P342_FX6_E_ND_STEPS, ("CLEAR", "1/4", "1/16", "1/64", "1/128"))
        for kw in (
            {"claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning": True},
            {"claimed_fx3_has_e_nd_or_apr": True},
        ):
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR)

    def test_62_gc_focus_assistant_exact_five_items_enforced(self) -> None:
        self.assertEqual(len(P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS), 5)
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            exposed_focus_assistant_items=P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS[:4]
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_63_gc_still_ff_focus_mag_scales_1_0_to_2_1_to_4_1(self) -> None:
        self.assertEqual(P342_STILL_FF_MAG_CYCLE_SCALES, (1.0, 2.1, 4.1))
        for scale in P342_STILL_FF_MAG_CYCLE_SCALES:
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
                shoot_mode="PHOTO", apsc_s35_shooting="OFF", requested_focus_mag_x=scale
            )
            self.assertTrue(gc.passed)
        gc_bad = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="PHOTO", apsc_s35_shooting="OFF", requested_focus_mag_x=4.0
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_64_gc_still_apsc_focus_mag_scales_1_0_to_1_5_to_3_0(self) -> None:
        self.assertEqual(P342_STILL_APSC_MAG_CYCLE_SCALES, (1.0, 1.5, 3.0))
        for scale in P342_STILL_APSC_MAG_CYCLE_SCALES:
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
                shoot_mode="PHOTO", apsc_s35_shooting="ON", requested_focus_mag_x=scale
            )
            self.assertTrue(gc.passed)
        gc_bad = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="PHOTO", apsc_s35_shooting="ON", requested_focus_mag_x=4.1
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_65_gc_movie_focus_mag_scales_1_0_to_4_0_only(self) -> None:
        self.assertEqual(P342_MOVIE_MAG_CYCLE_SCALES, (1.0, 4.0))
        for scale in P342_MOVIE_MAG_CYCLE_SCALES:
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
                shoot_mode="MOVIE", requested_focus_mag_x=scale
            )
            self.assertTrue(gc.passed)
        gc_bad = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="MOVIE", requested_focus_mag_x=2.1
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_66_gc_rejects_dormant_high_mp_focus_mag_scales(self) -> None:
        self.assertIn(5.3, P342_DORMANT_HIGH_MP_MAG_SCALES)
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            dormant_high_mp_focus_mag_scale_requested=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)
        self._assert_err_contains(gc, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_67_gc_focus_magnif_time_2s_5s_no_limit(self) -> None:
        for t in ("2_SEC", "5_SEC", "NO_LIMIT"):
            self.assertTrue(
                evaluate_p342_check_group_c_antidust_and_focus_assistant(focus_magnif_time=t).passed
            )
        self.assertFalse(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(focus_magnif_time="10_SEC").passed
        )

    def test_68_gc_rejects_still_only_af_in_focus_mag_and_auto_mag_in_movie(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="MOVIE", expect_af_in_focus_mag_or_auto_mag_in_movie=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_69_gc_movie_rec_persists_focus_mag_and_clean_hdmi_unzoomed(self) -> None:
        self.assertTrue(P342_FOCUS_MAG_PERSISTS_DURING_MOVIE_REC)
        self.assertFalse(P342_FOCUS_MAG_OUTPUTS_TO_HDMI)
        for kw in (
            {"claimed_movie_rec_cancels_focus_mag": True},
            {"expect_focus_mag_crops_hdmi_or_internal_rec": True},
        ):
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_70_gc_rejects_claimed_focus_assistant_wiped_by_camera_reset(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            claimed_focus_assistant_wiped_by_camera_reset=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY)

    def test_71_gc_fx6_vf_3x_6x_and_ver6_hdmi_2x_4x_parity(self) -> None:
        self.assertEqual(P342_FX6_VF_FOCUS_MAG_SCALES, (3.0, 6.0))
        self.assertEqual(P342_FX6_HDMI_FOCUS_MAG_SCALES, (2.0, 4.0))
        for kw in (
            {"claimed_fx6_hdmi_focus_mag_is_3x_6x": True},
            {"claimed_fx6_vf_focus_mag_is_2_1x_4_1x": True},
        ):
            gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY)

    def test_72_gc_invalid_initial_focus_mag_rejected(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="PHOTO", apsc_s35_shooting="OFF", initial_focus_mag_x=4.1
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI)

    def test_73_gc_still_ff_initial_2_1x_passes(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="PHOTO",
            apsc_s35_shooting="OFF",
            initial_focus_mag_x=2.1,
            requested_focus_mag_x=2.1,
        )
        self.assertTrue(gc.passed)

    def test_74_gc_still_apsc_initial_1_5x_passes(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="PHOTO",
            apsc_s35_shooting="ON",
            initial_focus_mag_x=1.5,
            requested_focus_mag_x=3.0,
        )
        self.assertTrue(gc.passed)

    def test_75_gc_movie_initial_4_0x_passes(self) -> None:
        gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
            shoot_mode="MOVIE",
            initial_focus_mag_x=4.0,
            requested_focus_mag_x=4.0,
        )
        self.assertTrue(gc.passed)

    def test_76_gc_invalid_af_in_focus_mag_or_auto_mag_rejected(self) -> None:
        self.assertFalse(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(af_in_focus_mag="AUTO").passed
        )
        self.assertFalse(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(auto_magnifier_in_mf="AUTO").passed
        )

    def test_77_gc_invalid_shoot_mode_or_apsc_rejected(self) -> None:
        self.assertFalse(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(shoot_mode="TIMELAPSE").passed
        )
        self.assertFalse(
            evaluate_p342_check_group_c_antidust_and_focus_assistant(apsc_s35_shooting="AUTO").passed
        )

    # ------------------------------------------------------------------
    # 78-100: Check Group D — Exposure Std. Adjust, USB-LAN/Tethering, Tier-0 H0==H3, CLI
    # ------------------------------------------------------------------

    def test_78_gd_exp_std_adjust_five_metering_modes_and_13_sixths(self) -> None:
        self.assertEqual(len(P342_EXP_STD_ADJ_FIVE_METERING_MODES), 5)
        self.assertEqual(P342_EXP_STD_ADJ_EXACT_STEPS, 13)
        self.assertEqual(P342_EXP_STD_ADJ_STEP_ENUM, "EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6")
        self.assertTrue(P342_EXP_STD_ADJ_RESET_IMMUNE)
        self.assertFalse(P342_EXP_STD_ADJ_MODIFIES_EXIF_BIAS)
        for mode in P342_EXP_STD_ADJ_FIVE_METERING_MODES:
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
                exp_std_adjust_metering_mode=mode,
                exp_std_adjust_sixths=0,
            )
            self.assertTrue(gd.passed)

    def test_79_gd_exp_std_nonzero_blocked_unless_acknowledged(self) -> None:
        gd_unack = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            exp_std_adjust_sixths=3, exp_std_nonzero_acknowledged=False
        )
        self.assertFalse(gd_unack.passed)
        self._assert_err(gd_unack, P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP)
        gd_ack = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            exp_std_adjust_sixths=-6, exp_std_nonzero_acknowledged=True
        )
        self.assertTrue(gd_ack.passed)
        self.assertEqual(gd_ack.exp_std_adjust_ev, -1.0)

    def test_80_gd_exp_std_rejects_out_of_range_and_dormant_1_8_ev(self) -> None:
        for kw in (
            {"exp_std_adjust_sixths": 7, "exp_std_nonzero_acknowledged": True},
            {"exp_std_adjust_sixths": -7, "exp_std_nonzero_acknowledged": True},
            {"dormant_1_8_ev_step_requested": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP)

    def test_81_gd_exp_std_rejects_exif_bias_cine_ei_iso_and_reset_myths(self) -> None:
        for kw in (
            {"expect_exp_std_adjust_modifies_exif_bias": True},
            {"expect_exp_std_changes_cine_ei_iso": True},
            {"claimed_exp_std_adjust_wiped_by_camera_reset": True},
            {"claimed_exp_std_adjust_resets_exposure_comp": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP)

    def test_82_gd_debunks_fx6_ae_level_2ev_myth_3ev_25_steps(self) -> None:
        self.assertEqual(P342_FX6_AE_LEVEL_MIN_EV, -3.0)
        self.assertEqual(P342_FX6_AE_LEVEL_MAX_EV, 3.0)
        self.assertEqual(P342_FX6_AE_LEVEL_STEP_EV, 0.25)
        self.assertEqual(P342_FX6_AE_LEVEL_EXACT_STEPS, 25)
        for ev in (-3.0, -2.25, 0.0, 2.5, 3.0):
            self.assertTrue(
                evaluate_p342_check_group_d_exp_std_usblan_and_tier0(fx6_ae_level_ev=ev).passed
            )
        for kw in (
            {"fx6_ae_level_ev": 3.25},
            {"fx6_ae_level_ev": 0.10},
            {"claimed_fx6_ae_level_limited_to_2ev": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH)

    def test_83_gd_usb_lan_tethering_works_with_airplane_mode_on_zero_rf(self) -> None:
        self.assertIn("libNetServiceTethering.so", P342_USB_LAN_LIBS)
        self.assertIn("cdc_ncm.ko", P342_USB_LAN_KERNEL_MODULES)
        self.assertIn("ipheth.ko", P342_USB_LAN_KERNEL_MODULES)
        for svc in ("RTMP", "RTMPS", "SRT", "FTP"):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
                usb_lan_tethering="ON",
                usb_lan_cnct_launch="ON",
                usb_lan_service=svc,
                airplane_mode="ON",
                wireless_rf_packets_emitted=0,
            )
            self.assertTrue(gd.passed)
            self.assertEqual(gd.airplane_mode, "ON")
            self.assertEqual(gd.wireless_rf_packets_emitted, 0)

    def test_84_gd_rejects_airplane_mode_off_and_dual_usb_port_mutex(self) -> None:
        gd_rf = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(airplane_mode="OFF")
        self.assertFalse(gd_rf.passed)
        self._assert_err(gd_rf, P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX)
        gd_dual = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            dual_usb_typec_and_multi_simultaneous=True
        )
        self.assertFalse(gd_dual.passed)
        self._assert_err(gd_dual, P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX)
        self._assert_err_contains(gd_dual, f"errno={P342_ERRNO_EBUSY}")

    def test_85_gd_rejects_dormant_usb_streaming_uvc(self) -> None:
        for kw in (
            {"usb_connection_mode": "USB_STREAMING"},
            {"claimed_usb_streaming_uvc_active_on_fx3": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX)
            self._assert_err_contains(gd, f"errno={P342_ERRNO_EOPNOTSUPP}")

    def test_86_gd_rejects_usb_lan_myths_and_emits_reset_network_warning(self) -> None:
        for kw in (
            {"claimed_airplane_mode_blocks_usb_lan": True},
            {"claimed_creators_app_allows_guided_live_over_usb": True},
            {"claimed_reset_network_preserves_airplane_mode": True},
            {"claimed_camera_reset_wipes_usb_tethering": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX)
        gd_warn = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            reset_action="RESET_NETWORK_SET"
        )
        self.assertTrue(gd_warn.passed)
        self.assertTrue(any("RESET_NETWORK_SET" in w for w in gd_warn.warnings))

    def test_87_gd_slot1_usb_host_write_blocked_erofs30_and_usbgmscif_readonly(self) -> None:
        self.assertEqual(P342_USBGMSCIF_READONLY_SYMBOL, "usbgmscif_setReadOnly")
        gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            slot1_contains_tier0_dump=True, slot1_host_usb_write_requested=True
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP)
        self._assert_err_contains(gd, f"errno={P342_ERRNO_EROFS}")
        self._assert_err_contains(gd, P342_USBGMSCIF_READONLY_SYMBOL)

    def test_88_gd_rejects_fx3_vs_fx6_cusbgadgetiap_myths(self) -> None:
        self.assertEqual(P342_FX3_CUSB_GADGET_IAP_HITS, 0)
        self.assertTrue(P342_FX6_CUSB_GADGET_IAP_PRESENT)
        for kw in (
            {"claimed_fx3_links_cusbgadgetiap": True},
            {"claimed_fx6_lacks_cusbgadgetiap": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP)

    def test_89_gd_tier0_receipt_rejects_same_stdev(self) -> None:
        sim = build_simulated_phase342_tier0_receipts()
        gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=42,
            st_dev_b_override=42,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_90_gd_tier0_receipt_rejects_copy_mismatch_and_bad_length(self) -> None:
        sim = build_simulated_phase342_tier0_receipts()
        bad_b = bytearray(sim["receipt_b_bytes"])
        bad_b[-1] ^= 0xFF
        gd_mis = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=bytes(bad_b),
            st_dev_a_override=1,
            st_dev_b_override=2,
        )
        self.assertFalse(gd_mis.passed)
        self._assert_err(gd_mis, P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
        gd_len = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            receipt_a_bytes=b"SHORT",
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
        )
        self.assertFalse(gd_len.passed)
        self._assert_err(gd_len, P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_91_gd_tier0_rejects_trivial_serial_and_trivial_cid(self) -> None:
        sim = build_simulated_phase342_tier0_receipts()
        for kw in (
            {"body_serial": "0000000000"},
            {"emmc_cid": "0" * 32},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=1,
                st_dev_b_override=2,
                **kw,
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_92_gd_h0_vs_h3_surface_drift_rejected(self) -> None:
        sim = build_simulated_phase342_tier0_receipts()
        drifted_h3 = dict(sim["h3_baselines"])
        surf0 = SIXTEEN_STORAGE_SURFACES[0]
        drifted_h3[surf0] = "f" * 64
        gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=drifted_h3,
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)
        self.assertEqual(gd.h0_equals_h3_count, 15)

    def test_93_gd_simulated_h0_h3_drift_rejected(self) -> None:
        gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=2
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_equals_h3_count, 14)
        self._assert_err(gd, P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_94_gd_fail_closed_redline_violations_rejected(self) -> None:
        for kw in (
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"wireless_rf_packets_emitted": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P342_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_95_physical_receipts_from_disk_files_with_distinct_stdev_mock(self) -> None:
        sim = build_simulated_phase342_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmpdir:
            p_a = Path(tmpdir) / "FX3RCPT1_A.bin"
            p_b = Path(tmpdir) / "FX3RCPT1_B.bin"
            p_a.write_bytes(sim["receipt_a_bytes"])
            p_b.write_bytes(sim["receipt_b_bytes"])
            gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
                receipt_a_path=p_a,
                receipt_b_path=p_b,
                st_dev_a_override=901,
                st_dev_b_override=902,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
                h3_baselines=sim["h3_baselines"],
            )
            self.assertTrue(gd.passed)
            self.assertTrue(gd.tier0_receipt_verified)
            self.assertEqual(gd.h0_equals_h3_count, 16)

    def test_96_direct_fx6_cli_main_entrypoint_clean_room_dry_run_and_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_json = Path(tmpdir) / "p342.json"
            out_md = Path(tmpdir) / "p342.md"
            rc_dry = fx6_cli_main(
                [
                    "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--output",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                ]
            )
            self.assertEqual(rc_dry, 0)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            parsed = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema_version"], P342_SCHEMA)
            self.assertTrue(verify_phase342_report(parsed).valid)
            rc_def = fx6_cli_main(
                [
                    "preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether",
                    "--force-clean-room",
                    "--summary",
                ]
            )
            self.assertEqual(rc_def, 2)

    def test_97_cli_subprocess_help_exits_0_and_contains_percent_escaped_cleanly(self) -> None:
        cp = _run_cli_subprocess(["--help"])
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("preflight-peaking-audio-wind-usb-pd-ntsc-pal-antidust-focus-mag-expstd-and-usbtether", cp.stdout)

    def test_98_cli_subprocess_default_exits_2_awaiting_receipt(self) -> None:
        cp = _run_cli_subprocess(["--force-clean-room", "--json"])
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(data["overall_ready_for_hardware_attach"])

    def test_99_cli_subprocess_dry_run_exits_0_in_clean_room(self) -> None:
        cp = _run_cli_subprocess(
            ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertTrue(verify_phase342_report(data).valid)

    def test_100_cli_subprocess_failure_flags_exit_2(self) -> None:
        cp = _run_cli_subprocess(
            [
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--expect-peaking-outputs-over-hdmi",
                "--json",
            ]
        )
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(
            data["go_no_go"],
            P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE,
        )
        self.assertIn(P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP, data["errors"][0])


if __name__ == "__main__":
    unittest.main()
