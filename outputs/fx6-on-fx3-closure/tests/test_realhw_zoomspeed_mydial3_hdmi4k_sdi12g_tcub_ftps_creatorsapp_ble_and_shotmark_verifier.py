"""Four-mode unit tests (112 cases) for Phase 371
(`preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark`
+ short alias `preflight-phase371`):
24th Physical Bench Readiness Verifier across Global Sony Waves 79-80 check groups (`A..D`):
- Group A (Wave 79 Zoom Speed Split & Dial Customize 5-Item / Zero-EVF Operation Customize):
  - `[Zoom Range]` (`OPTICAL_ONLY`/`CLEAR_IMAGE_ZOOM` `4K 1.5x, HD 2.0x`/`DIGITAL_ZOOM` `4.0x`;
    `Smart Zoom` Still M/S non-RAW only; resists Reset) & `[Zoom Ring Rotate]` (resists Reset)
    vs Resettable speed trio: `[Zoom Lever Speed]` (`1st=3, 2nd=8` Stby/REC), `[Custom Key Z.
    Speed]` (Fixed `1..8` ONLY, zero `Variable` mode), and `[Remote Zoom Speed]` (`VARIABLE`/`FIX`
    via `BKID_APP_setting_fixed_zoom_speed_type` + `1..8`), plus CIZ/Digital lockouts (`RAW`,
    `100/120p`, `S&Q>=100fps`, HDMI `RAW`, Focus Area/Tracking/Face AF/Multi-Metering lockouts)
    vs FX6 `Zoom Type` (no Digital Zoom) & `Handle Zoom` (`0..99` is HUD position display only).
  - `[Dial Customize]` strictly 5 Initialize-only items (`Custom Key/Dial Set.`, `My Dial
    Settings` temporary unlock of `Lock Operation Parts`, `Av/Tv Rotate`, `Function Ring(Lens)`
    `POWER_FOCUS` vs `APSC_S35_FF`, `Lock Operation Parts`; dormant `Dial Setup`/`Dial/Wheel
    Lock`/`Rear Dial L/R` rejected `EOPNOTSUPP=95`). `[Different Set for Still/Mv]` 8-bit mask
    (`Picture Profile` resists BOTH Reset & Initialize; `[Shutter Mode]=Angle` forces split) vs
    `12+12` `Fn` slots (forbids all-Not-set), 4 Monitor `[DISP]` pages (`Graphic Display` &
    entire `[Finder/Monitor]` dormant on EVF-less FX3), and `[Select LUT]`/`[Display LUT]` vs
    `[Gamma Display Assist]` (inactive in Movie when `Log Shooting != Off`).
- Group B (Wave 79 External Output HDMI 4K 10-bit/RAW vs FX6 12G-SDI Dual-Pipeline):
  - FX3 `[HDMI Resolution]` strictly 4 options (`AUTO`/`2160P`/`1080P`/`1080I`, zero `720p`),
    `[4K Output Set.(HDMI Only)]` strictly 6 `10bit` `4:2:2` modes (no `4:2:0`, dormant
    `24.00p 8bit` & `24p/60p Output` rejected, `24.00p` `MODEL_EVENT_REBOOT_BY_CROSS_2400P`
    reboot gate & APS-C restriction), `[HDMI Info. Display]=On` LCD blanking strictly when
    `Rec. Media = On & RAW = Off` (auto-Clean HDMI + active LCD under `Off(HDMI Only)` or
    `RAW = On`), internal Log/PPLUT 1080p clamp, `[REC Control]` requiring `Time Code Output=ON`
    and non-S&Q, and 3 Sony ELF typos (`BKID_APP_setting_ctrl_for_hmdi`,
    `PRM_HAITA_hdmi_4k_outpute_apsc_restriction`, `BKID_APP_setting_4ch_output_ch`) vs FX6
    25-combo `12G/6G/3G-SDI + HDMI` matrix (`SDI/HDMI Remote I/F` vs `Parallel Rec`, VF stays
    active, `S&Q > 60fps` HDMI clamp, HDMI RAW `4240x2392` clamping SDI to 1080p/i).
- Group C (Wave 80 `[TC/UB]` `VMC-BNCM1` TC-IN-Only & `[FTP Transfer Func.]` Explicit `FTPES` /
  `Slot 1` `.DAT`):
  - All 7 FX3 `[TC/UB]` + `[TC/UB Disp. Setting]` items resist `[Camera Settings Reset]`
    (`Initialize`/Delete/FW update clear `Preset`; Sony typo
    `VAL_setting_tc_make_TC_MAKE_REGENRATE`); `DF`/`NDF` selectable strictly on NTSC
    `29.97p`/`59.94p`/`119.88p` (`23.98p`/`24.00p`/PAL locked `NDF`); `VMC-BNCM1` unidirectional
    `TC-IN-Only` via `BODY_MULTI_MICRO_USB` (`Preset` + `Free Run` -> `EXT-LK` + freewheel,
    forbidden on `XLR_H1_HANDLE_PORT`) vs FX6 physical BNC `TC IN/OUT` switch + `Clock` mode +
    hex-only `Users Bit` (`Title1(ASCII)` is Clip Title).
  - FX3 `[FTP Transfer Func.]` (`Server 1..9`, plaintext `FTP` & Explicit `AUTH TLS` `FTPES`
    via OpenSSL 3.0 `libInfraFtpClient.so` `PASSIVE` only; zero `SSH_SFTP` / `IMPLICIT_FTPS`;
    `Slot 1` `cacert.pem` & `SONY/SETTING/<Model>/FTPSET/FTPSET01..10.DAT` password-encrypted
    + mandatory reboot -> blocked `EROFS=30` on Tier-0 `Slot 1`) vs FX6 `File Transfer` (`Slot B`
    `certification.pem`, Active/Passive, Chunk Proxy upload).
- Group D (Wave 80 `Creators' App` 5-GATT BLE / `G114` `[Airplane Mode]` Erratum & Playback
  `Shot Mark`/`Rating`/`Protect`/`Copy` `Slot 1 EROFS=30` + Tier-0 Dual-Media Receipt Gate):
  - `Creators' App` 5 BLE GATT tables (`8000CC00/DD00/EE00/FF00/BB00`), Ver. 3.00+ migration of
    `[Location Info. Link Set.]` to smartphone app (`8000DD00`), `bt_stack.conf`
    `LMP_WAKEUP_CONFIG` `[Cnct. while Power OFF]`, BLE pairing wiped by `[Reset Network Set.]`
    & `[Initialize]` (resists `[Camera Settings Reset]`), and **Wave 80 `G114` erratum**:
    `[Airplane Mode]=On` is NOT cleared by `[Reset Network Set.]` (`Initialize`-only) +
    mandatory electrical isolation of `USB-LAN` (`rf_tx_packets == 0`).
  - Playback write matrix (`libmpr.so` / `libInfraFsys.so`): `[Add/Delete Shot Mark 1/2]`
    (`*M01.XML` + `AVF_INFO`), `[Rating]`, `[Protect]`, `[Delete]`, and asymmetric `[Copy]`
    (`SLOT_1_TO_SLOT_2` read-only safe on `Slot 1` vs `SLOT_2_TO_SLOT_1` blocked `EROFS=30`,
    `slot1_sector_writes == 0`) vs FX6 `Clip Flag` (`OK`/`NG`/`KEEP`).
  - `16/16 H0 == H3` dual-media `528 B FX3RCPT1` Tier-0 gate & hard-locked
    `overall_ready_for_hardware_attach=False`.

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`,
`FX3_FX6_FORCE_CLEAN_ROOM=1`, and mocked donorless (`work_root=None`) modes with
zero `.pyc` emission and zero persistent writes.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
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
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    REQUIRED_H0_BASELINE_KEYS,
    build_default_h0_baselines,
)
from fx6_closure.realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier import (  # noqa: E402
    P371_4CH_AUDIO_OUTPUT_MODES,
    P371_BLE_EXACT_5_GATT_TABLES,
    P371_BLE_MAX_CONCURRENT_LINKS,
    P371_BLE_MAX_PAIRED_DEVICES,
    P371_BOUNDED_DONOR_PATHS,
    P371_BT_STACK_WAKEUP_KEY,
    P371_CHECK_GROUP_A_ID,
    P371_CHECK_GROUP_B_ID,
    P371_CHECK_GROUP_C_ID,
    P371_CHECK_GROUP_D_ID,
    P371_COPY_DIRECTIONS,
    P371_CUSTOM_KEY_ZOOM_MODES,
    P371_DIAL_CUSTOMIZE_DORMANT_ITEMS,
    P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS,
    P371_DIFF_SET_EXACT_8_ITEMS,
    P371_DORMANT_EVF_DISP_ITEMS,
    P371_ERRNO_EBUSY,
    P371_ERRNO_EINVAL,
    P371_ERRNO_EOPNOTSUPP,
    P371_ERRNO_EPERM,
    P371_ERRNO_EROFS,
    P371_FN_MENU_MOVIE_SLOTS,
    P371_FN_MENU_STILL_SLOTS,
    P371_FTP_CACERT_FILENAME,
    P371_FTP_CACERT_MAX_BYTES,
    P371_FTP_FORBIDDEN_PROTOCOLS,
    P371_FTP_PROTOCOLS,
    P371_FTP_SERVER_SLOTS_MAX,
    P371_FTP_TRANSFER_MODES,
    P371_FTPSET_SLOTS_MAX,
    P371_FTPSET_TEMPLATE,
    P371_FUNCTION_RING_MODES,
    P371_FX6_BNC_TC_SWITCH_MODES,
    P371_FX6_CACERT_FILENAME,
    P371_FX6_CACERT_SLOT,
    P371_FX6_CLIP_FLAGS,
    P371_FX6_HANDLE_ZOOM_HUD_RANGE,
    P371_FX6_HANDLE_ZOOM_MODES,
    P371_FX6_HDMI_RAW_RES_STR,
    P371_FX6_REC_SYNC_MODES,
    P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT,
    P371_FX6_SDI_MODES,
    P371_FX6_TC_MAKE_MODES,
    P371_FX6_ZOOM_TYPES,
    P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD,
    P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK,
    P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT,
    P371_GA_ERR_MODEL_OR_FW_FLOOR,
    P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED,
    P371_GAMMA_DISP_ASSIST_TYPES,
    P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC,
    P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP,
    P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT,
    P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE,
    P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30,
    P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT,
    P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE,
    P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB,
    P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET,
    P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION,
    P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30,
    P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P371_GO_NO_GO_BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE,
    P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED,
    P371_HDMI_4K_DORMANT_MODES,
    P371_HDMI_4K_OUTPUT_EXACT_6_MODES,
    P371_HDMI_RESOLUTION_DORMANT,
    P371_HDMI_RESOLUTIONS_EXACT_4,
    P371_HEADER_READ_BYTES,
    P371_LOCK_OPERATION_PARTS_MODES,
    P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES,
    P371_MY_DIAL_SLOTS,
    P371_NTSC_DF_CAPABLE_FPS,
    P371_OUTPUT_RESOLUTIONS,
    P371_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P371_PLAYBACK_WRITE_OPS,
    P371_PPLUT_PROFILES,
    P371_RAW_OUTPUT_RES_STR,
    P371_RAW_OUTPUT_SETTINGS,
    P371_REBOOT_2400P_EVENT,
    P371_REC_MEDIA_DUR_HDMI_MODES,
    P371_REMOTE_ZOOM_SPEED_TYPE_BKID,
    P371_REMOTE_ZOOM_SPEED_TYPES,
    P371_SCHEMA,
    P371_SELECT_LUT_PRESETS,
    P371_SMART_ZOOM_STILL_M_MAX,
    P371_SMART_ZOOM_STILL_S_MAX,
    P371_SONY_ELF_TYPOS,
    P371_SONY_HELP_GUIDE_ID,
    P371_STORAGE_SURFACE_COUNT,
    P371_TC_FORMAT_MODES,
    P371_TC_MAKE_MODES,
    P371_TC_MAKE_TYPO_SYMBOL,
    P371_TC_RUN_MODES,
    P371_TCUB_DISP_MODES,
    P371_TCUB_EXACT_7_ITEMS,
    P371_VERSION,
    P371_VMC_BNCM1_PART,
    P371_VMC_DIRECTIONS,
    P371_VMC_PORT_MODES,
    P371_ZOOM_CIZ_MAX_4K,
    P371_ZOOM_CIZ_MAX_HD,
    P371_ZOOM_DIGITAL_MAX,
    P371_ZOOM_LEVER_1ST_DEFAULT,
    P371_ZOOM_LEVER_2ND_DEFAULT,
    P371_ZOOM_RANGE_MODES,
    P371_ZOOM_RING_ROTATE_MODES,
    P371_ZOOM_SPEED_MAX,
    P371_ZOOM_SPEED_MIN,
    RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport,
    build_simulated_phase371_tier0_receipts,
    evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf,
    evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g,
    evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1,
    evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0,
    evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight,
    inspect_phase371_donors_bounded,
    render_phase371_markdown,
    run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight,
    verify_phase371_report,
)

PYTHONPATH_ENV = ":".join(
    str(REPO_ROOT / p)
    for p in (
        "outputs/fx6-on-fx3-closure",
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
    )
)
VERIFIER_MOD = (
    "fx6_closure.realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_verifier"
)
CLI_CMD_LONG = "preflight-zoomspeed-mydial3-hdmi4k-sdi12g-tcub-ftps-creatorsapp-ble-and-shotmark"
CLI_CMD_ALIAS = "preflight-phase371"


class TestPhase371Preflight24Verifier(unittest.TestCase):
    def _assert_err(self, res: object, code: str) -> None:
        errs = getattr(res, "errors", ())
        self.assertTrue(
            any(code in e for e in errs),
            msg=f"Expected error prefix {code!r} in {errs!r}",
        )

    def _run_cli(
        self,
        args: list[str],
        *,
        env_overrides: dict[str, str] | None = None,
        clear_clean_room_env: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        if clear_clean_room_env:
            env.pop("FX3_CLEAN_ROOM_TEST", None)
            env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            env.pop("FX3_FX6_MAC_WORK_ROOT", None)
        if env_overrides:
            env.update(env_overrides)
        env["PYTHONPATH"] = PYTHONPATH_ENV
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "-m", "fx6_closure", *args],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    # ------------------------------------------------------------------
    # 1. Exports, Non-Shadowing & Bounded O_RDONLY / 4-Mode Parity (10)
    # ------------------------------------------------------------------

    def test_001_package_exports_and_all_contain_phase371_symbols(self) -> None:
        required = (
            "P371_SCHEMA",
            "P371_VERSION",
            "evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf",
            "evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g",
            "evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1",
            "evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0",
            "evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight",
            "run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight",
            "verify_phase371_report",
            "render_phase371_markdown",
            "build_simulated_phase371_tier0_receipts",
            "inspect_phase371_donors_bounded",
            "resolve_phase371_donor_file_or_none",
            "RealHwZoomSpeedMyDial3Hdmi4kSdi12gTcUbFtpsCreatorsAppBleAndShotMarkReport",
        )
        for sym in required:
            self.assertTrue(hasattr(fx6_closure, sym), msg=f"Missing export {sym}")
            self.assertIn(sym, fx6_closure.__all__, msg=f"Missing __all__ entry {sym}")

    def test_002_no_shadowing_of_phase368_and_milestone364_exports(self) -> None:
        self.assertNotEqual(fx6_closure.P368_SCHEMA, fx6_closure.P371_SCHEMA)
        self.assertEqual(fx6_closure.P371_SCHEMA, P371_SCHEMA)
        self.assertEqual(fx6_closure.P371_VERSION, P371_VERSION)
        self.assertTrue(hasattr(fx6_closure, "evaluate_milestone_364_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "verify_milestone_364_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "verify_phase368_report"))

    def test_003_bounded_donor_paths_count_and_constants(self) -> None:
        self.assertEqual(len(P371_BOUNDED_DONOR_PATHS), 9)
        self.assertEqual(P371_HEADER_READ_BYTES, 64)
        self.assertEqual(P371_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(P371_STORAGE_SURFACE_COUNT, 16)
        self.assertEqual(P371_ERRNO_EPERM, 1)
        self.assertEqual(P371_ERRNO_EBUSY, 16)
        self.assertEqual(P371_ERRNO_EINVAL, 22)
        self.assertEqual(P371_ERRNO_EROFS, 30)
        self.assertEqual(P371_ERRNO_EOPNOTSUPP, 95)

    def test_004_donor_inspection_force_clean_room_and_env_variants(self) -> None:
        d_flag = inspect_phase371_donors_bounded(force_clean_room=True)
        self.assertEqual(d_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(d_flag.donor_tree_present)
        self.assertEqual(d_flag.bytes_read_total, 0)
        self.assertEqual(d_flag.raw_firmware_bytes_leaked, 0)

        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            d_env1 = inspect_phase371_donors_bounded()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            d_env2 = inspect_phase371_donors_bounded()
        self.assertEqual(d_env1.header_digests, d_flag.header_digests)
        self.assertEqual(d_env2.header_digests, d_flag.header_digests)

    def test_005_donor_inspection_mocked_work_root_none_synthetic(self) -> None:
        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            d = inspect_phase371_donors_bounded(force_clean_room=False)
        self.assertEqual(d.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(d.donor_tree_present)
        self.assertEqual(d.bytes_read_total, 0)
        self.assertEqual(d.raw_firmware_bytes_leaked, 0)

    def test_006_donor_inspection_nonexistent_work_root_fallback(self) -> None:
        d = inspect_phase371_donors_bounded(
            force_clean_room=False,
            work_root=Path("/nonexistent/phase371_missing_donor_root"),
        )
        self.assertEqual(d.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(d.donor_tree_present)
        self.assertEqual(d.raw_firmware_bytes_leaked, 0)

    def test_007_donor_inspection_synthetic_temp_donors_reads_exact_64b(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx6_dir = Path(td) / "fx6"
            fx3_dir = Path(td) / "fx3"
            fx6_dir.mkdir()
            fx3_dir.mkdir()
            (fx6_dir / "appFw.so").write_bytes(b"FX6_ELF_" + b"A" * 512)
            (fx3_dir / "appFw.so").write_bytes(b"FX3_ELF_" + b"B" * 512)
            (fx3_dir / "libInfraFtpClient.so").write_bytes(b"FTP_ELF_" + b"C" * 512)
            (fx3_dir / "libInfraBluetoothLowEnergy.so").write_bytes(b"BLE_ELF_" + b"D" * 512)
            with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
                d = inspect_phase371_donors_bounded(
                    force_clean_room=False,
                    fx6_lib_dir=fx6_dir,
                    fx3_modules_dir=fx3_dir,
                )
            self.assertEqual(d.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(d.donor_tree_present)
            self.assertGreaterEqual(d.donors_present, 4)
            self.assertEqual(d.bytes_read_total, d.donors_present * 64)
            self.assertEqual(d.raw_firmware_bytes_leaked, 0)

    def test_008_timing_stripping_removes_elapsed_fields_from_sha256(self) -> None:
        rep_a = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        rep_b = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep_a.report_sha256, rep_b.report_sha256)
        payload = rep_a.to_dict()
        payload["donor_inspection"]["elapsed_seconds"] = 99.123456
        self.assertTrue(verify_phase371_report(payload).valid)

    def test_009_check_group_ids_exact_four_and_baseline_pass(self) -> None:
        rep = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep.check_group_count, 4)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertEqual(rep.check_group_a.group_id, P371_CHECK_GROUP_A_ID)
        self.assertEqual(rep.check_group_b.group_id, P371_CHECK_GROUP_B_ID)
        self.assertEqual(rep.check_group_c.group_id, P371_CHECK_GROUP_C_ID)
        self.assertEqual(rep.check_group_d.group_id, P371_CHECK_GROUP_D_ID)

    def test_010_offline_awaiting_receipts_status_and_go_no_go(self) -> None:
        rep = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=False
        )
        self.assertEqual(rep.overall_status, P371_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase371_report(rep).valid)

    # ------------------------------------------------------------------
    # 2. Group A — Wave 79 Zoom Speed Split, Lockouts & FX6 Handle HUD (15)
    # ------------------------------------------------------------------

    def test_011_group_a_model_fw_and_help_guide_floor(self) -> None:
        ga_ok = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf()
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_bad_id = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            body_model_id=0xDEADBEEF
        )
        self.assertFalse(ga_bad_id.passed)
        self._assert_err(ga_bad_id, P371_GA_ERR_MODEL_OR_FW_FLOOR)

        ga_bad_fw = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            body_fw="6.01"
        )
        self.assertFalse(ga_bad_fw.passed)
        self._assert_err(ga_bad_fw, P371_GA_ERR_MODEL_OR_FW_FLOOR)

        ga_bad_hg = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            sony_help_guide_id="ilc/9999"
        )
        self.assertFalse(ga_bad_hg.passed)
        self._assert_err(ga_bad_hg, P371_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_012_group_a_zoom_range_magnification_constants_and_modes(self) -> None:
        self.assertEqual(P371_ZOOM_RANGE_MODES, ("OPTICAL_ONLY", "CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM"))
        self.assertEqual(P371_ZOOM_CIZ_MAX_4K, 1.5)
        self.assertEqual(P371_ZOOM_CIZ_MAX_HD, 2.0)
        self.assertEqual(P371_ZOOM_DIGITAL_MAX, 4.0)
        for zr in P371_ZOOM_RANGE_MODES:
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                zoom_range=zr, face_eye_prior_in_af="OFF", face_priority_in_multi_metering="OFF"
            )
            self.assertTrue(ga.passed, msg=f"{zr}: {ga.errors}")

    def test_013_group_a_zoom_range_and_ring_rotate_resist_camera_reset(self) -> None:
        ga_cam = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_ring_rotate="RIGHT_W_LEFT_T",
            face_eye_prior_in_af="OFF",
            face_priority_in_multi_metering="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ga_cam.passed, msg=ga_cam.errors)
        self.assertEqual(ga_cam.effective_zoom_range_after_reset, "CLEAR_IMAGE_ZOOM")
        self.assertEqual(ga_cam.effective_zoom_ring_rotate_after_reset, "RIGHT_W_LEFT_T")

        ga_init = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_range="CLEAR_IMAGE_ZOOM",
            zoom_ring_rotate="RIGHT_W_LEFT_T",
            face_eye_prior_in_af="OFF",
            face_priority_in_multi_metering="OFF",
            reset_action="INITIALIZE",
        )
        self.assertTrue(ga_init.passed)
        self.assertEqual(ga_init.effective_zoom_range_after_reset, "OPTICAL_ONLY")
        self.assertEqual(ga_init.effective_zoom_ring_rotate_after_reset, "LEFT_W_RIGHT_T")

    def test_014_group_a_zoom_reset_claims_rejected(self) -> None:
        for kw in (
            {"claimed_zoom_range_wiped_by_camera_reset": True},
            {"claimed_zoom_ring_rotate_wiped_by_camera_reset": True},
            {"claimed_zoom_speeds_resist_camera_reset": True},
        ):
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    def test_015_group_a_resettable_zoom_speed_trio_1st_3_2nd_8_and_reset(self) -> None:
        self.assertEqual(P371_ZOOM_SPEED_MIN, 1)
        self.assertEqual(P371_ZOOM_SPEED_MAX, 8)
        self.assertEqual(P371_ZOOM_LEVER_1ST_DEFAULT, 3)
        self.assertEqual(P371_ZOOM_LEVER_2ND_DEFAULT, 8)
        ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_lever_stby_1st=5,
            zoom_lever_stby_2nd=7,
            custom_key_zoom_stby_speed=6,
            remote_zoom_speed_type="FIX",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ga.passed, msg=ga.errors)
        self.assertEqual(ga.effective_zoom_lever_stby_1st_after_reset, 3)
        self.assertEqual(ga.effective_custom_key_zoom_stby_after_reset, 3)
        self.assertEqual(ga.effective_remote_zoom_type_after_reset, "VARIABLE")

    def test_016_group_a_zoom_speed_out_of_range_1_to_8_rejected(self) -> None:
        for bad in (0, 9):
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                zoom_lever_stby_1st=bad
            )
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    def test_017_group_a_custom_key_zoom_fixed_only_zero_variable_mode(self) -> None:
        self.assertEqual(P371_CUSTOM_KEY_ZOOM_MODES, ("FIXED",))
        ga_var = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            custom_key_zoom_mode="VARIABLE"
        )
        self.assertFalse(ga_var.passed)
        self._assert_err(ga_var, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_custom_key_zoom_has_variable_mode=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    def test_018_group_a_remote_zoom_speed_bkid_variable_and_fix(self) -> None:
        self.assertEqual(P371_REMOTE_ZOOM_SPEED_TYPES, ("VARIABLE", "FIX"))
        self.assertEqual(P371_REMOTE_ZOOM_SPEED_TYPE_BKID, "BKID_APP_setting_fixed_zoom_speed_type")
        for rtype in P371_REMOTE_ZOOM_SPEED_TYPES:
            self.assertTrue(
                evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                    remote_zoom_speed_type=rtype
                ).passed
            )
        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            remote_zoom_speed_type="AUTO"
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    def test_019_group_a_smart_zoom_still_m_s_non_raw_only(self) -> None:
        self.assertEqual(P371_SMART_ZOOM_STILL_M_MAX, 1.5)
        self.assertEqual(P371_SMART_ZOOM_STILL_S_MAX, 2.0)
        self.assertTrue(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                shoot_mode="PHOTO",
                still_file_format="JPEG",
                still_image_size="M",
                smart_zoom_requested=True,
            ).passed
        )
        self.assertTrue(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                shoot_mode="PHOTO",
                still_file_format="HEIF",
                still_image_size="S",
                smart_zoom_requested=True,
            ).passed
        )
        for bad_kw in (
            {"shoot_mode": "PHOTO", "still_file_format": "RAW", "still_image_size": "M"},
            {"shoot_mode": "PHOTO", "still_file_format": "JPEG", "still_image_size": "L"},
            {"shoot_mode": "MOVIE", "still_file_format": "JPEG", "still_image_size": "M"},
        ):
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                smart_zoom_requested=True, **bad_kw
            )
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

    def test_020_group_a_ciz_digital_lockouts_raw_120p_sq100_hdmi_raw(self) -> None:
        lockout_cases = (
            {"shoot_mode": "PHOTO", "still_file_format": "RAW"},
            {"shoot_mode": "MOVIE", "rec_frame_rate_fps": 119.88},
            {"shoot_mode": "S_AND_Q", "sq_frame_rate_fps": 120},
            {"hdmi_raw_output": True},
        )
        for kw in lockout_cases:
            ga_blk = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                zoom_range="CLEAR_IMAGE_ZOOM",
                face_eye_prior_in_af="OFF",
                face_priority_in_multi_metering="OFF",
                **kw,
            )
            self.assertFalse(ga_blk.passed)
            self._assert_err(ga_blk, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

            ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                expect_ciz_active_under_lockout=True, **kw
            )
            self.assertFalse(ga_claim.passed)
            self._assert_err(ga_claim, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

    def test_021_group_a_ciz_locks_focus_area_tracking_face_af_and_metering(self) -> None:
        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_range="CLEAR_IMAGE_ZOOM",
            face_eye_prior_in_af="OFF",
            expect_focus_area_or_tracking_under_ciz=True,
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

        ga_track = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_range="DIGITAL_ZOOM",
            tracking_af_active=True,
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(ga_track.passed)
        self._assert_err(ga_track, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

        ga_spot = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_range="CLEAR_IMAGE_ZOOM",
            metering_mode="SPOT",
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(ga_spot.passed)
        self._assert_err(ga_spot, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

    def test_022_group_a_fx6_zoom_type_zero_digital_zoom(self) -> None:
        self.assertEqual(P371_FX6_ZOOM_TYPES, ("OPTICAL_ONLY", "CLEAR_IMAGE_ZOOM"))
        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            fx6_zoom_type="DIGITAL_ZOOM"
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_fx6_has_digital_zoom=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

    def test_023_group_a_fx6_handle_zoom_modes_and_0_99_hud_not_speed(self) -> None:
        self.assertEqual(P371_FX6_HANDLE_ZOOM_MODES, ("OFF", "LOW", "HIGH", "VARIABLE"))
        self.assertEqual(P371_FX6_HANDLE_ZOOM_HUD_RANGE, (0, 99))
        for mode in P371_FX6_HANDLE_ZOOM_MODES:
            self.assertTrue(
                evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                    fx6_handle_zoom_mode=mode, fx6_handle_zoom_hud_position=99
                ).passed
            )
        ga_oob = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            fx6_handle_zoom_hud_position=100
        )
        self.assertFalse(ga_oob.passed)
        self._assert_err(ga_oob, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_fx6_0_99_is_speed_scale=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_CIZ_DIGITAL_LOCKOUT_OR_FX6_HANDLE_HUD)

    def test_024_group_a_zoom_ring_rotate_invalid_rejected(self) -> None:
        self.assertEqual(P371_ZOOM_RING_ROTATE_MODES, ("LEFT_W_RIGHT_T", "RIGHT_W_LEFT_T"))
        ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_ring_rotate="UP_DOWN"
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    def test_025_group_a_rec_vs_stby_zoom_lever_speeds_validated(self) -> None:
        ga_ok = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_lever_stby_1st=1,
            zoom_lever_stby_2nd=8,
            zoom_lever_rec_1st=2,
            zoom_lever_rec_2nd=6,
        )
        self.assertTrue(ga_ok.passed)
        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            zoom_lever_rec_2nd=10
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_ZOOM_SPLIT_RESET_OR_CUSTOM_KEY_FIXED)

    # ------------------------------------------------------------------
    # 3. Group A — Dial Customize 5-Item, DiffSet-8, Fn 12+12, Zero-EVF, LUT (15)
    # ------------------------------------------------------------------

    def test_026_group_a_dial_customize_exact_5_items_initialize_only(self) -> None:
        self.assertEqual(len(P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS), 5)
        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            dial_customize_items=P371_DIAL_CUSTOMIZE_EXACT_5_ITEMS[:4]
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_dial_customize_wiped_by_camera_reset=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK)

    def test_027_group_a_dormant_dial_customize_items_rejected_eopnotsupp(self) -> None:
        self.assertEqual(
            P371_DIAL_CUSTOMIZE_DORMANT_ITEMS, ("Dial Setup", "Dial/Wheel Lock", "Rear Dial L/R")
        )
        for dormant in P371_DIAL_CUSTOMIZE_DORMANT_ITEMS:
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                dormant_dial_customize_item_requested=dormant
            )
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK)
            self._assert_err(ga, f"EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP}")

    def test_028_group_a_my_dial_1_2_3_temporarily_unlocks_lock_operation_parts(self) -> None:
        self.assertEqual(P371_MY_DIAL_SLOTS, (1, 2, 3))
        for slot in P371_MY_DIAL_SLOTS:
            ga_ok = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                my_dial_slot=slot, my_dial_active=True, lock_operation_parts="DIAL_AND_WHEEL"
            )
            self.assertTrue(ga_ok.passed, msg=ga_ok.errors)
            self.assertTrue(ga_ok.my_dial_temporarily_unlocks_lock_op)

        ga_bad_slot = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            my_dial_slot=4
        )
        self.assertFalse(ga_bad_slot.passed)
        self._assert_err(ga_bad_slot, P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK)

        ga_block_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            expect_lock_op_blocks_my_dial=True
        )
        self.assertFalse(ga_block_claim.passed)
        self._assert_err(ga_block_claim, P371_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_MY_DIAL_UNLOCK)

    def test_029_group_a_function_ring_lens_and_av_tv_rotate_and_lock_parts(self) -> None:
        self.assertEqual(P371_FUNCTION_RING_MODES, ("POWER_FOCUS", "APSC_S35_FF"))
        for fr in P371_FUNCTION_RING_MODES:
            for rot in ("NORMAL", "REVERSE"):
                for lock_mode in P371_LOCK_OPERATION_PARTS_MODES:
                    self.assertTrue(
                        evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                            function_ring_lens=fr,
                            av_tv_rotate=rot,
                            lock_operation_parts=lock_mode,
                        ).passed
                    )
        self.assertFalse(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                function_ring_lens="ZOOM_RING"
            ).passed
        )

    def test_030_group_a_diff_set_exact_8_items_and_pp_dual_immunity(self) -> None:
        self.assertEqual(len(P371_DIFF_SET_EXACT_8_ITEMS), 8)
        self.assertIn("Picture Profile", P371_DIFF_SET_EXACT_8_ITEMS)
        for rst in ("CAMERA_SETTINGS_RESET", "INITIALIZE"):
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                diff_set_pp_checked=True, reset_action=rst
            )
            self.assertTrue(ga.passed)
            self.assertTrue(ga.effective_diff_set_pp_after_reset)

        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            diff_set_items=P371_DIFF_SET_EXACT_8_ITEMS[:7]
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_pp_diffset_wiped_by_reset_or_init=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_031_group_a_shutter_mode_angle_forces_still_movie_split(self) -> None:
        ga_ok = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            shutter_mode="ANGLE"
        )
        self.assertTrue(ga_ok.passed)
        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            shutter_mode="ANGLE", expect_shutter_angle_shares_still_movie=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_032_group_a_fn_menu_12_plus_12_slots_forbids_all_not_set(self) -> None:
        self.assertEqual(P371_FN_MENU_STILL_SLOTS, 12)
        self.assertEqual(P371_FN_MENU_MOVIE_SLOTS, 12)
        ga_bad_slots = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            fn_menu_still_slots=10
        )
        self.assertFalse(ga_bad_slots.passed)
        self._assert_err(ga_bad_slots, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

        ga_not_set = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            fn_menu_all_not_set_requested=True
        )
        self.assertFalse(ga_not_set.passed)
        self._assert_err(ga_not_set, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_033_group_a_monitor_disp_exact_4_pages_zero_evf_firewall(self) -> None:
        self.assertEqual(len(P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES), 4)
        self.assertEqual(
            P371_DORMANT_EVF_DISP_ITEMS,
            ("Graphic Display", "For viewfinder", "Monitor Off", "Finder/Monitor"),
        )
        ga_bad_pages = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            monitor_disp_pages=P371_MONITOR_DISP_EXACT_4_SHOOT_PAGES + ("Graphic Display",)
        )
        self.assertFalse(ga_bad_pages.passed)
        self._assert_err(ga_bad_pages, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_034_group_a_dormant_evf_finder_graphic_display_rejected_eopnotsupp(self) -> None:
        for dormant in P371_DORMANT_EVF_DISP_ITEMS:
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                dormant_evf_disp_requested=dormant
            )
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)
            self._assert_err(ga, f"EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP}")

        ga_evf = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            claimed_fx3_has_builtin_evf=True
        )
        self.assertFalse(ga_evf.passed)
        self._assert_err(ga_evf, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_035_group_a_select_lut_presets_and_user1_to_user16(self) -> None:
        self.assertEqual(P371_SELECT_LUT_PRESETS, ("S-Log3", "s709", "709(800%)"))
        for lut in (*P371_SELECT_LUT_PRESETS, "User1", "User16"):
            self.assertTrue(
                evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                    select_lut=lut, display_lut="ON"
                ).passed
            )
        ga_bad = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            select_lut="User17"
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_036_group_a_gamma_display_assist_inactive_when_log_shooting_on(self) -> None:
        self.assertEqual(
            P371_GAMMA_DISP_ASSIST_TYPES, ("AUTO", "SLOG3_TO_709_800", "HLG_BT2020", "HLG_709")
        )
        ga_pp_movie = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            shoot_mode="MOVIE", log_shooting_mode="OFF", gamma_display_assist="ON"
        )
        self.assertTrue(ga_pp_movie.passed)
        self.assertTrue(ga_pp_movie.gamma_display_assist_active_in_movie)

        ga_log_movie = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            shoot_mode="MOVIE", log_shooting_mode="CINE_EI", gamma_display_assist="ON"
        )
        self.assertTrue(ga_log_movie.passed)
        self.assertFalse(ga_log_movie.gamma_display_assist_active_in_movie)

        ga_claim = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
            shoot_mode="MOVIE",
            log_shooting_mode="FLEXIBLE_ISO",
            expect_gamma_assist_active_in_log_movie=True,
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P371_GA_ERR_DIFFSET8_PP_IMMUNITY_ZERO_EVF_OR_LUT)

    def test_037_group_a_invalid_shoot_or_log_or_reset_action_rejected(self) -> None:
        for kw in (
            {"shoot_mode": "TIMELAPSE"},
            {"log_shooting_mode": "CUSTOM_EI"},
            {"reset_action": "FACTORY_WIPE"},
        ):
            ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(**kw)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P371_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_038_group_a_invalid_av_tv_rotate_or_lock_op_parts_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                av_tv_rotate="DIAGONAL"
            ).passed
        )
        self.assertFalse(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                lock_operation_parts="SHUTTER_ONLY"
            ).passed
        )

    def test_039_group_a_invalid_display_lut_or_gamma_assist_on_off_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                display_lut="AUTO"
            ).passed
        )
        self.assertFalse(
            evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf(
                gamma_display_assist="AUTO"
            ).passed
        )

    def test_040_group_a_fx3_builtin_evf_always_false_in_result(self) -> None:
        ga = evaluate_p371_check_group_a_zoomspeed_mydial3_diffset8_and_zeroevf()
        self.assertFalse(ga.fx3_builtin_evf_present)

    # ------------------------------------------------------------------
    # 4. Group B — Wave 79 External Output HDMI 4K 10-bit/RAW vs FX6 12G-SDI (18)
    # ------------------------------------------------------------------

    def test_041_group_b_hdmi_resolution_exact_4_options_zero_720p(self) -> None:
        self.assertEqual(P371_HDMI_RESOLUTIONS_EXACT_4, ("AUTO", "2160P", "1080P", "1080I"))
        self.assertEqual(P371_HDMI_RESOLUTION_DORMANT, ("720P",))
        for res in P371_HDMI_RESOLUTIONS_EXACT_4:
            self.assertTrue(
                evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(hdmi_resolution=res).passed
            )
        gb_720 = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(hdmi_resolution="720P")
        self.assertFalse(gb_720.passed)
        self._assert_err(gb_720, P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT)

        gb_claim = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            claimed_hdmi_has_720p_or_420=True
        )
        self.assertFalse(gb_claim.passed)
        self._assert_err(gb_claim, P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT)

    def test_042_group_b_hdmi_4k_output_set_exact_6_10bit_422_modes(self) -> None:
        self.assertEqual(len(P371_HDMI_4K_OUTPUT_EXACT_6_MODES), 6)
        for m in P371_HDMI_4K_OUTPUT_EXACT_6_MODES:
            self.assertTrue(m.endswith("_10BIT_422"))
            self.assertTrue(
                evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
                    hdmi_4k_output_set=m, prev_hdmi_4k_output_set=m
                ).passed
            )
        gb_bad_opts = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_4k_output_options_exposed=P371_HDMI_4K_OUTPUT_EXACT_6_MODES[:5]
        )
        self.assertFalse(gb_bad_opts.passed)
        self._assert_err(gb_bad_opts, P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT)

    def test_043_group_b_dormant_hdmi_4k_modes_rejected_eopnotsupp(self) -> None:
        self.assertEqual(P371_HDMI_4K_DORMANT_MODES, ("24_00P_8BIT", "24P_60P_OUTPUT", "4K_420_8BIT"))
        for dormant in P371_HDMI_4K_DORMANT_MODES:
            gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
                dormant_hdmi_4k_mode_requested=dormant
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT)
            self._assert_err(gb, f"EOPNOTSUPP={P371_ERRNO_EOPNOTSUPP}")

    def test_044_group_b_2400p_cross_reboot_gate_and_apsc_restriction(self) -> None:
        gb_no_ack = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_4k_output_set="24_00P_10BIT_422",
            prev_hdmi_4k_output_set="23_98P_10BIT_422",
            reboot_2400p_acknowledged=False,
        )
        self.assertFalse(gb_no_ack.passed)
        self._assert_err(gb_no_ack, P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE)

        gb_ack = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_4k_output_set="24_00P_10BIT_422",
            prev_hdmi_4k_output_set="23_98P_10BIT_422",
            reboot_2400p_acknowledged=True,
        )
        self.assertTrue(gb_ack.passed)
        self.assertTrue(gb_ack.reboot_2400p_gate_triggered)

        gb_apsc = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_4k_output_set="24_00P_10BIT_422",
            prev_hdmi_4k_output_set="24_00P_10BIT_422",
            apsc_s35_shooting="ON",
        )
        self.assertFalse(gb_apsc.passed)
        self._assert_err(gb_apsc, P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE)

    def test_045_group_b_external_output_resists_camera_reset(self) -> None:
        gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            claimed_external_output_wiped_by_camera_reset=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P371_GB_ERR_HDMI_RES_4OPT_OR_4K_6MODE_10BIT)

    def test_046_group_b_hdmi_info_display_blanks_lcd_when_rec_on_raw_off(self) -> None:
        gb_blank = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output=False,
            hdmi_info_display="ON",
        )
        self.assertTrue(gb_blank.passed)
        self.assertTrue(gb_blank.fx3_lcd_blanked_for_hdmi_info)
        self.assertEqual(gb_blank.effective_hdmi_info_display, "ON")

        gb_claim = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output=False,
            hdmi_info_display="ON",
            expect_fx3_lcd_active_when_rec_on_info_on_raw_off=True,
        )
        self.assertFalse(gb_claim.passed)
        self._assert_err(gb_claim, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

    def test_047_group_b_auto_clean_hdmi_and_active_lcd_under_off_hdmi_only_or_raw_on(self) -> None:
        gb_ext = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            hdmi_raw_output=False,
            hdmi_info_display="ON",
        )
        self.assertTrue(gb_ext.passed)
        self.assertEqual(gb_ext.effective_hdmi_info_display, "OFF")
        self.assertFalse(gb_ext.fx3_lcd_blanked_for_hdmi_info)

        gb_raw = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output=True,
            hdmi_info_display="ON",
        )
        self.assertTrue(gb_raw.passed)
        self.assertEqual(gb_raw.effective_hdmi_info_display, "OFF")
        self.assertFalse(gb_raw.fx3_lcd_blanked_for_hdmi_info)

    def test_048_group_b_internal_log_or_pplut_clamps_hdmi_to_1080p(self) -> None:
        gb_log = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            log_shooting_mode="FLEXIBLE_ISO",
            rec_media_dur_hdmi_output="ON",
            output_resolution="2160P",
        )
        self.assertTrue(gb_log.passed)
        self.assertEqual(gb_log.effective_output_resolution, "1080P")

        gb_pplut = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            picture_profile="PPLUT1",
            rec_media_dur_hdmi_output="ON",
            output_resolution="AUTO",
        )
        self.assertTrue(gb_pplut.passed)
        self.assertEqual(gb_pplut.effective_output_resolution, "1080P")

        gb_claim = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="ON",
            expect_4k_internal_hdmi_when_log_or_pplut=True,
        )
        self.assertFalse(gb_claim.passed)
        self._assert_err(gb_claim, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

    def test_049_group_b_raw_output_16bit_requires_movie_and_log_and_no_color_gamut(self) -> None:
        self.assertEqual(P371_RAW_OUTPUT_RES_STR, "4264x2408_16BIT")
        gb_no_log = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_raw_output=True, log_shooting_mode="OFF"
        )
        self.assertFalse(gb_no_log.passed)
        self._assert_err(gb_no_log, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

        gb_photo = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            shoot_mode="PHOTO", hdmi_raw_output=True, log_shooting_mode="CINE_EI"
        )
        self.assertFalse(gb_photo.passed)
        self._assert_err(gb_photo, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

        gb_gamut = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            claimed_color_gamut_for_raw_output_present=True
        )
        self.assertFalse(gb_gamut.passed)
        self._assert_err(gb_gamut, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

    def test_050_group_b_rec_control_requires_tc_output_on_and_non_sq(self) -> None:
        self.assertTrue(
            evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
                hdmi_time_code_output="ON", hdmi_rec_control="ON", shoot_mode="MOVIE"
            ).passed
        )
        gb_no_tc = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_time_code_output="OFF", hdmi_rec_control="ON"
        )
        self.assertFalse(gb_no_tc.passed)
        self._assert_err(gb_no_tc, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

        gb_sq = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            shoot_mode="S_AND_Q", hdmi_time_code_output="ON", hdmi_rec_control="ON"
        )
        self.assertFalse(gb_sq.passed)
        self._assert_err(gb_sq, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

        gb_sq_off_hdmi = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            shoot_mode="S_AND_Q", rec_media_dur_hdmi_output="OFF_HDMI_ONLY"
        )
        self.assertFalse(gb_sq_off_hdmi.passed)
        self._assert_err(gb_sq_off_hdmi, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

    def test_051_group_b_sony_elf_typos_and_4ch_audio_output_exact(self) -> None:
        self.assertEqual(
            P371_SONY_ELF_TYPOS,
            (
                "BKID_APP_setting_ctrl_for_hmdi",
                "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
                "BKID_APP_setting_4ch_output_ch",
            ),
        )
        gb_bad_typo = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            sony_elf_typos_verified=("BKID_APP_setting_ctrl_for_hdmi",)
        )
        self.assertFalse(gb_bad_typo.passed)
        self._assert_err(gb_bad_typo, P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE)

        for ch in P371_4CH_AUDIO_OUTPUT_MODES:
            self.assertTrue(
                evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(hdmi_4ch_audio_output=ch).passed
            )
        gb_bad_ch = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            hdmi_4ch_audio_output="CH1_TO_4"
        )
        self.assertFalse(gb_bad_ch.passed)
        self._assert_err(gb_bad_ch, P371_GB_ERR_SONY_ELF_TYPOS_OR_24P_REBOOT_GATE)

    def test_052_group_b_fx6_25_combo_12g_sdi_hdmi_matrix_and_rec_sync(self) -> None:
        self.assertEqual(P371_FX6_SDI_HDMI_MATRIX_COMBO_COUNT, 25)
        self.assertEqual(P371_FX6_SDI_MODES, ("12G_SDI", "6G_SDI", "3G_SDI", "OFF"))
        self.assertEqual(P371_FX6_REC_SYNC_MODES, ("OFF", "SDI_HDMI_REMOTE_IF", "PARALLEL_REC"))
        for sdi in P371_FX6_SDI_MODES:
            for sync in P371_FX6_REC_SYNC_MODES:
                self.assertTrue(
                    evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
                        fx6_sdi_mode=sdi, fx6_rec_sync_mode=sync
                    ).passed
                )
        gb_bad_cnt = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(fx6_sdi_hdmi_combo_count=16)
        self.assertFalse(gb_bad_cnt.passed)
        self._assert_err(gb_bad_cnt, P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC)

    def test_053_group_b_fx6_hdmi_raw_24hz_and_builtin_vf_and_sq_clamp_claims(self) -> None:
        self.assertEqual(P371_FX6_HDMI_RAW_RES_STR, "4240x2392")
        for kw in (
            {"claimed_fx6_hdmi_raw_supports_24hz_or_4k_sdi": True},
            {"claimed_fx6_builtin_vf_blanks_like_fx3_lcd": True},
            {"claimed_fx6_sq_above_60fps_keeps_4k_hdmi_with_sdi_on": True},
            {"fx6_sq_fps": 120, "fx6_sdi_mode": "12G_SDI", "fx6_hdmi_mode": "3840x2160_59_94P"},
        ):
            gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(**kw)
            self.assertFalse(gb.passed)
            self._assert_err(gb, P371_GB_ERR_FX6_SDI12G_25COMBO_OR_PARALLEL_REC)

    def test_054_group_b_fx6_sq_above_60fps_ok_when_hdmi_1080p(self) -> None:
        gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            fx6_sq_fps=120, fx6_sdi_mode="12G_SDI", fx6_hdmi_mode="1920x1080_59_94P"
        )
        self.assertTrue(gb.passed)
        self.assertTrue(gb.fx6_builtin_vf_active)

    def test_055_group_b_raw_output_setting_accepts_all_6_frame_rates(self) -> None:
        self.assertEqual(len(P371_RAW_OUTPUT_SETTINGS), 6)
        for rate in P371_RAW_OUTPUT_SETTINGS:
            self.assertTrue(
                evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
                    log_shooting_mode="CINE_EI",
                    hdmi_raw_output=True,
                    raw_output_setting=rate,
                ).passed
            )

    def test_056_group_b_output_resolution_options_all_4_valid(self) -> None:
        self.assertEqual(P371_OUTPUT_RESOLUTIONS, ("AUTO", "2160P", "1080P", "1080I"))
        for r in P371_OUTPUT_RESOLUTIONS:
            self.assertTrue(
                evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(output_resolution=r).passed
            )
        self.assertFalse(
            evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(output_resolution="720P").passed
        )

    def test_057_group_b_rec_ctrl_without_tc_claim_flag_rejected(self) -> None:
        gb = evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(
            expect_rec_ctrl_without_tc_output_or_in_sq=True
        )
        self.assertFalse(gb.passed)
        self._assert_err(gb, P371_GB_ERR_HDMI_INFO_LCD_BLANK_RAW_OR_1080_CLAMP)

    def test_058_group_b_invalid_fx6_sdi_or_sync_mode_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(fx6_sdi_mode="24G_SDI").passed
        )
        self.assertFalse(
            evaluate_p371_check_group_b_hdmi4k_and_fx6_sdi12g(fx6_rec_sync_mode="GENLOCK").passed
        )

    # ------------------------------------------------------------------
    # 5. Group C — Wave 80 [TC/UB] VMC-BNCM1 TC-IN-Only & FX6 BNC/Hex UB (15)
    # ------------------------------------------------------------------

    def test_059_group_c_tcub_exact_7_items_resist_camera_settings_reset(self) -> None:
        self.assertEqual(len(P371_TCUB_EXACT_7_ITEMS), 7)
        gc_rst = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_port="DISCONNECTED",
            tc_make="REGENERATE",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(gc_rst.passed, msg=gc_rst.errors)
        self.assertEqual(gc_rst.effective_tc_make_after_reset, "REGENERATE")
        self.assertFalse(gc_rst.tc_preset_cleared_on_reset)

        gc_bad = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            tcub_items_exposed=P371_TCUB_EXACT_7_ITEMS[:6]
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE)

    def test_060_group_c_initialize_or_delete_or_fw_update_clears_tc_preset(self) -> None:
        gc_init = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_port="DISCONNECTED",
            tc_make="REGENERATE",
            reset_action="INITIALIZE",
        )
        self.assertTrue(gc_init.passed, msg=gc_init.errors)
        self.assertEqual(gc_init.effective_tc_make_after_reset, "PRESET")
        self.assertTrue(gc_init.tc_preset_cleared_on_reset)

        gc_del = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            tc_preset_delete_or_fw_update=True
        )
        self.assertTrue(gc_del.passed)
        self.assertTrue(gc_del.tc_preset_cleared_on_reset)

    def test_061_group_c_tcub_reset_claim_and_sony_tc_make_regenrate_typo(self) -> None:
        self.assertEqual(P371_TC_MAKE_TYPO_SYMBOL, "VAL_setting_tc_make_TC_MAKE_REGENRATE")
        gc_claim = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            claimed_tcub_wiped_by_camera_reset=True
        )
        self.assertFalse(gc_claim.passed)
        self._assert_err(gc_claim, P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE)

        gc_typo = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            tc_make_typo_symbol="VAL_setting_tc_make_TC_MAKE_REGENERATE"
        )
        self.assertFalse(gc_typo.passed)
        self._assert_err(gc_typo, P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE)

    def test_062_group_c_df_ndf_strictly_ntsc_2997_5994_11988_only(self) -> None:
        self.assertEqual(P371_NTSC_DF_CAPABLE_FPS, (29.97, 59.94, 119.88))
        for fps in P371_NTSC_DF_CAPABLE_FPS:
            self.assertTrue(
                evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                    video_system="NTSC", rec_fps=fps, tc_format="DF"
                ).passed
            )
        for bad_sys, bad_fps in (("NTSC", 23.98), ("NTSC", 24.0), ("PAL", 25.0), ("PAL", 50.0)):
            gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                video_system=bad_sys, rec_fps=bad_fps, tc_format="DF"
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE)

        gc_ndf_ok = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            video_system="NTSC", rec_fps=23.98, tc_format="NDF"
        )
        self.assertTrue(gc_ndf_ok.passed)

    def test_063_group_c_df_claim_and_sq_tc_run_lockout_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                expect_df_selectable_on_2398_2400_or_pal=True
            ).passed
        )
        gc_sq = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            shoot_mode="S_AND_Q", vmc_bncm1_port="DISCONNECTED", expect_tc_run_active_in_sq=True
        )
        self.assertFalse(gc_sq.passed)
        self._assert_err(gc_sq, P371_GC_ERR_TCUB_7ITEM_RESET_OR_DF_NDF_RULE)

    def test_064_group_c_vmc_bncm1_body_usb_tc_in_only_ext_lk_and_freewheel(self) -> None:
        self.assertEqual(P371_VMC_BNCM1_PART, "VMC-BNCM1")
        gc_ok = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_port="BODY_MULTI_MICRO_USB",
            vmc_bncm1_direction="TC_IN_ONLY",
            shoot_mode="MOVIE",
            tc_make="PRESET",
            tc_run="FREE_RUN",
            ext_lk_freewheel_after_unplug=True,
        )
        self.assertTrue(gc_ok.passed)
        self.assertEqual(gc_ok.ext_lk_status, "EXT-LK")

    def test_065_group_c_vmc_bncm1_xlr_h1_port_and_tc_out_forbidden(self) -> None:
        gc_xlr = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_port="XLR_H1_HANDLE_PORT"
        )
        self.assertFalse(gc_xlr.passed)
        self._assert_err(gc_xlr, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

        gc_out = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_direction="TC_OUT"
        )
        self.assertFalse(gc_out.passed)
        self._assert_err(gc_out, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

        gc_bnc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            claimed_fx3_has_bnc_tc_out_or_clock_mode=True
        )
        self.assertFalse(gc_bnc.passed)
        self._assert_err(gc_bnc, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

    def test_066_group_c_vmc_bncm1_ext_lk_requires_preset_free_run_and_freewheel(self) -> None:
        for kw in (
            {"tc_make": "REGENERATE"},
            {"tc_run": "REC_RUN"},
            {"ext_lk_freewheel_after_unplug": False},
        ):
            gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                vmc_bncm1_port="BODY_MULTI_MICRO_USB", **kw
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

    def test_067_group_c_fx6_bnc_switch_clock_mode_and_hex_only_users_bit(self) -> None:
        self.assertEqual(P371_FX6_BNC_TC_SWITCH_MODES, ("TC_IN", "TC_OUT"))
        self.assertEqual(P371_FX6_TC_MAKE_MODES, ("PRESET", "REGENERATE", "CLOCK"))
        for sw in P371_FX6_BNC_TC_SWITCH_MODES:
            for mk in P371_FX6_TC_MAKE_MODES:
                self.assertTrue(
                    evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                        fx6_bnc_tc_switch=sw, fx6_tc_make=mk, fx6_users_bit_hex="CAFEBABE"
                    ).passed
                )

    def test_068_group_c_fx6_users_bit_rejects_ascii_title1_or_non_hex(self) -> None:
        gc_nonhex = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            fx6_users_bit_hex="TITLE123"
        )
        self.assertFalse(gc_nonhex.passed)
        self._assert_err(gc_nonhex, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

        gc_claim = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            claimed_fx6_users_bit_ascii_title1=True
        )
        self.assertFalse(gc_claim.passed)
        self._assert_err(gc_claim, P371_GC_ERR_VMC_BNCM1_TC_IN_ONLY_OR_FX6_BNC_UB)

    def test_069_group_c_tcub_disp_setting_modes_validated(self) -> None:
        self.assertEqual(P371_TCUB_DISP_MODES, ("COUNTER", "TC", "U_BIT"))
        for disp in P371_TCUB_DISP_MODES:
            self.assertTrue(
                evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                    tcub_disp_setting=disp
                ).passed
            )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                tcub_disp_setting="CLIP_NAME"
            ).passed
        )

    def test_070_group_c_tc_format_run_make_enums_validated(self) -> None:
        self.assertEqual(P371_TC_FORMAT_MODES, ("DF", "NDF"))
        self.assertEqual(P371_TC_RUN_MODES, ("REC_RUN", "FREE_RUN"))
        self.assertEqual(P371_TC_MAKE_MODES, ("PRESET", "REGENERATE"))
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(tc_format="AUTO").passed
        )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(tc_run="CLOCK_RUN").passed
        )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(tc_make="CLOCK").passed
        )

    def test_071_group_c_vmc_bncm1_disconnected_yields_internal_unjammed(self) -> None:
        gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            vmc_bncm1_port="DISCONNECTED"
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.ext_lk_status, "INTERNAL_UNJAMMED")

    def test_072_group_c_fx6_invalid_bnc_switch_or_tc_make_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                fx6_bnc_tc_switch="BIDIR"
            ).passed
        )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                fx6_tc_make="JAM_SYNC"
            ).passed
        )

    def test_073_group_c_vmc_port_and_direction_enums_validated(self) -> None:
        self.assertEqual(
            P371_VMC_PORT_MODES, ("DISCONNECTED", "BODY_MULTI_MICRO_USB", "XLR_H1_HANDLE_PORT")
        )
        self.assertEqual(P371_VMC_DIRECTIONS, ("NONE", "TC_IN_ONLY", "TC_OUT"))
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                vmc_bncm1_port="SDI_BNC"
            ).passed
        )

    # ------------------------------------------------------------------
    # 6. Group C — Wave 80 [FTP Transfer Func.] Explicit FTPES & Slot 1 .DAT (11)
    # ------------------------------------------------------------------

    def test_074_group_c_ftp_server_1_to_9_and_explicit_ftpes_passive_only(self) -> None:
        self.assertEqual(P371_FTP_SERVER_SLOTS_MAX, 9)
        self.assertEqual(P371_FTP_PROTOCOLS, ("NONE", "FTP", "FTPES_EXPLICIT_AUTH_TLS"))
        self.assertEqual(P371_FTP_TRANSFER_MODES, ("PASSIVE",))
        for proto in P371_FTP_PROTOCOLS:
            self.assertTrue(
                evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                    ftp_transfer_func="ON", ftp_server_slot=9, ftp_protocol=proto
                ).passed
            )
        gc_slot10 = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(ftp_server_slot=10)
        self.assertFalse(gc_slot10.passed)
        self._assert_err(gc_slot10, P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT)

    def test_075_group_c_ftp_forbids_ssh_sftp_implicit_ftps_and_active_mode(self) -> None:
        self.assertEqual(P371_FTP_FORBIDDEN_PROTOCOLS, ("SSH_SFTP", "IMPLICIT_FTPS"))
        for bad_proto in P371_FTP_FORBIDDEN_PROTOCOLS:
            gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(ftp_protocol=bad_proto)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT)

        gc_act = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftp_transfer_mode="ACTIVE"
        )
        self.assertFalse(gc_act.passed)
        self._assert_err(gc_act, P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT)

        gc_claim = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            claimed_fx3_supports_sftp_or_implicit_ftps_or_active=True
        )
        self.assertFalse(gc_claim.passed)
        self._assert_err(gc_claim, P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT)

    def test_076_group_c_ftp_cloud_connection_mutual_exclusion(self) -> None:
        gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftp_transfer_func="ON", cloud_connection="ON"
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P371_GC_ERR_FTPES_EXPLICIT_PASSIVE_OR_SFTP_REJECT)

    def test_077_group_c_slot1_cacert_import_blocked_erofs30(self) -> None:
        self.assertEqual(P371_FTP_CACERT_FILENAME, "cacert.pem")
        self.assertEqual(P371_FTP_CACERT_MAX_BYTES, 1024 * 1024)
        gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftp_cacert_import_requested=True, ftp_cacert_slot=1
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30)
        self._assert_err(gc, f"EROFS={P371_ERRNO_EROFS}")

    def test_078_group_c_cacert_slot2_or_oversize_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(ftp_cacert_slot=2).passed
        )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                ftp_cacert_size_bytes=P371_FTP_CACERT_MAX_BYTES + 1
            ).passed
        )

    def test_079_group_c_ftpset01_10_dat_save_to_slot1_blocked_erofs30(self) -> None:
        self.assertEqual(P371_FTPSET_TEMPLATE, "SONY/SETTING/<Model>/FTPSET/FTPSET%02d.DAT")
        self.assertEqual(P371_FTPSET_SLOTS_MAX, 10)
        gc_save1 = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftpset_slot=1, ftpset_action="SAVE", ftpset_target_slot=1
        )
        self.assertFalse(gc_save1.passed)
        self._assert_err(gc_save1, P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30)
        self._assert_err(gc_save1, f"EROFS={P371_ERRNO_EROFS}")

        gc_save2 = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftpset_slot=10, ftpset_action="SAVE", ftpset_target_slot=2
        )
        self.assertTrue(gc_save2.passed)

    def test_080_group_c_ftpset_password_encryption_and_reboot_and_cross_model_gates(self) -> None:
        for kw in (
            {"ftpset_encrypted_with_password": False},
            {"ftpset_action": "LOAD", "ftpset_load_reboot_acknowledged": False},
            {"ftpset_cross_model_requested": True},
        ):
            gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(**kw)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30)

        gc_load_ok = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            ftpset_slot=3, ftpset_action="LOAD", ftpset_load_reboot_acknowledged=True
        )
        self.assertTrue(gc_load_ok.passed)

    def test_081_group_c_slot1_sector_writes_nonzero_blocked(self) -> None:
        gc = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(slot1_sector_writes=1)
        self.assertFalse(gc.passed)
        self._assert_err(gc, P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30)

    def test_082_group_c_fx6_file_transfer_certification_pem_slot_b_and_chunk_proxy(self) -> None:
        self.assertEqual(P371_FX6_CACERT_FILENAME, "certification.pem")
        self.assertEqual(P371_FX6_CACERT_SLOT, "SLOT_B")
        gc_ok = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1()
        self.assertTrue(gc_ok.passed)
        self.assertTrue(gc_ok.fx6_chunk_proxy_upload_enabled)

        gc_bad = evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
            fx6_file_transfer_cacert="cacert.pem"
        )
        self.assertFalse(gc_bad.passed)
        self._assert_err(gc_bad, P371_GC_ERR_FTP_SLOT1_CACERT_FTPSET_DAT_EROFS30)

    def test_083_group_c_ftpset_slot_bounds_1_to_10(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(ftpset_slot=0).passed
        )
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(ftpset_slot=11).passed
        )

    def test_084_group_c_ftp_transfer_func_invalid_enum_rejected(self) -> None:
        self.assertFalse(
            evaluate_p371_check_group_c_tcub_vmc_bncm1_and_ftpes_slot1(
                ftp_transfer_func="AUTO"
            ).passed
        )

    # ------------------------------------------------------------------
    # 7. Group D — Creators' App 5-GATT BLE, G114 Airplane, Playback Shot Mark (15)
    # ------------------------------------------------------------------

    def test_085_group_d_creators_app_5_ble_gatt_tables_and_ver3_location(self) -> None:
        self.assertEqual(
            P371_BLE_EXACT_5_GATT_TABLES,
            ("8000CC00", "8000DD00", "8000EE00", "8000FF00", "8000BB00"),
        )
        self.assertEqual(P371_BLE_MAX_PAIRED_DEVICES, 15)
        self.assertEqual(P371_BLE_MAX_CONCURRENT_LINKS, 2)
        self.assertEqual(P371_BT_STACK_WAKEUP_KEY, "LMP_WAKEUP_CONFIG")

        gd_bad_tbl = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, ble_gatt_tables_exposed=P371_BLE_EXACT_5_GATT_TABLES[:4]
        )
        self.assertFalse(gd_bad_tbl.passed)
        self._assert_err(gd_bad_tbl, P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET)

        gd_bad_loc = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, location_info_migrated_to_app_ver3=False
        )
        self.assertFalse(gd_bad_loc.passed)
        self._assert_err(gd_bad_loc, P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET)

    def test_086_group_d_ble_pairing_reset_matrix_vs_camera_settings_reset(self) -> None:
        gd_cam = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            creators_app_paired_count=3,
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(gd_cam.passed)
        self.assertEqual(gd_cam.effective_ble_paired_after_reset, 3)

        for rst in ("RESET_NETWORK_SET", "INITIALIZE"):
            gd_wipe = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True,
                creators_app_paired_count=3,
                reset_action=rst,
            )
            self.assertTrue(gd_wipe.passed)
            self.assertEqual(gd_wipe.effective_ble_paired_after_reset, 0)

    def test_087_group_d_ble_reset_claims_and_fx6_zero_ble_rejected(self) -> None:
        for kw in (
            {"claimed_ble_survives_reset_network_set": True},
            {"claimed_ble_wiped_by_camera_settings_reset": True},
            {"claimed_fx6_has_creators_app_ble_or_airplane_mode": True},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET)

    def test_088_group_d_wave80_g114_airplane_mode_erratum_not_cleared_by_reset_network_set(
        self,
    ) -> None:
        gd_net = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            airplane_mode="ON",
            reset_action="RESET_NETWORK_SET",
        )
        self.assertTrue(gd_net.passed)
        self.assertEqual(gd_net.effective_airplane_mode_after_reset, "ON")

        gd_init = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            airplane_mode="ON",
            reset_action="INITIALIZE",
        )
        self.assertTrue(gd_init.passed)
        self.assertEqual(gd_init.effective_airplane_mode_after_reset, "OFF")

    def test_089_group_d_g114_erratum_claims_and_airplane_off_rejected(self) -> None:
        for kw in (
            {"airplane_mode": "OFF"},
            {"cnct_while_power_off": "ON", "airplane_mode": "ON"},
            {"claimed_reset_network_set_clears_airplane_mode": True},
            {"claimed_initialize_preserves_airplane_mode": True},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION)

    def test_090_group_d_usb_lan_isolation_mandatory_for_zero_rf_bench(self) -> None:
        for kw in (
            {"usb_lan_electrically_isolated": False},
            {"expect_airplane_mode_isolates_usb_lan": True},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_G114_AIRPLANE_ERRATUM_OR_USBLAN_RF_ISOLATION)

    def test_091_group_d_playback_shotmark_rating_protect_delete_slot1_blocked_erofs30(self) -> None:
        for op in (
            "ADD_SHOT_MARK_1",
            "ADD_SHOT_MARK_2",
            "DELETE_SHOT_MARK_1",
            "DELETE_SHOT_MARK_2",
            "RATING",
            "PROTECT",
            "DELETE",
        ):
            gd_s1 = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True,
                playback_write_op=op,
                playback_target_slot=1,
            )
            self.assertFalse(gd_s1.passed)
            self._assert_err(gd_s1, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)
            self._assert_err(gd_s1, f"EROFS={P371_ERRNO_EROFS}")

            gd_s2 = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True,
                playback_write_op=op,
                playback_target_slot=2,
            )
            self.assertTrue(gd_s2.passed, msg=f"{op} Slot 2 failed: {gd_s2.errors}")

    def test_092_group_d_asymmetric_copy_slot1_to_slot2_safe_vs_slot2_to_slot1_erofs30(self) -> None:
        self.assertEqual(P371_COPY_DIRECTIONS, ("NONE", "SLOT_1_TO_SLOT_2", "SLOT_2_TO_SLOT_1"))
        gd_safe = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            playback_write_op="COPY",
            playback_copy_direction="SLOT_1_TO_SLOT_2",
        )
        self.assertTrue(gd_safe.passed)
        self.assertTrue(gd_safe.copy_slot1_to_slot2_readonly_safe)

        gd_blk = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            playback_write_op="COPY",
            playback_copy_direction="SLOT_2_TO_SLOT_1",
        )
        self.assertFalse(gd_blk.passed)
        self._assert_err(gd_blk, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)
        self._assert_err(gd_blk, f"EROFS={P371_ERRNO_EROFS}")

    def test_093_group_d_fx6_clip_flag_ok_ng_keep_and_zero_shotmark0_9_copy(self) -> None:
        self.assertEqual(P371_FX6_CLIP_FLAGS, ("NONE", "OK", "NG", "KEEP"))
        for flag in P371_FX6_CLIP_FLAGS:
            self.assertTrue(
                evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                    simulate_bench_dry_run=True, fx6_clip_flag=flag
                ).passed
            )
        gd_claim = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True,
            claimed_fx6_supports_shotmark0_9_or_in_camera_copy=True,
        )
        self.assertFalse(gd_claim.passed)
        self._assert_err(gd_claim, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)

    def test_094_group_d_claimed_copy_slot2_to_slot1_safe_rejected(self) -> None:
        gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, claimed_copy_slot2_to_slot1_safe=True
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)

    def test_095_group_d_rating_stars_0_to_5_bounds(self) -> None:
        for r in range(6):
            self.assertTrue(
                evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                    simulate_bench_dry_run=True, playback_write_op="RATING", rating_stars=r
                ).passed
            )
        gd_bad = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, rating_stars=6
        )
        self.assertFalse(gd_bad.passed)
        self._assert_err(gd_bad, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)

    def test_096_group_d_ble_paired_count_0_to_15_bounds(self) -> None:
        self.assertTrue(
            evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, creators_app_paired_count=15
            ).passed
        )
        gd_16 = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, creators_app_paired_count=16
        )
        self.assertFalse(gd_16.passed)
        self._assert_err(gd_16, P371_GD_ERR_CREATORS_APP_5GATT_BLE_WAKE_OR_RESET)

    def test_097_group_d_invalid_playback_op_or_copy_dir_or_fx6_flag_rejected(self) -> None:
        self.assertEqual(len(P371_PLAYBACK_WRITE_OPS), 9)
        for kw in (
            {"playback_write_op": "TRIM_CLIP"},
            {"playback_copy_direction": "SLOT_1_TO_USB"},
            {"fx6_clip_flag": "STAR5"},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_PLAYBACK_SHOTMARK_COPY_SLOT1_EROFS30)

    def test_098_group_d_telemetry_counters_nonzero_fail_closed(self) -> None:
        for kw in (
            {"slot1_sector_writes": 1},
            {"emmc_write_count": 1},
            {"e_nd_actuator_tx_count": 1},
            {"rf_tx_packets": 1},
            {"usb_packets_transmitted": 1},
            {"simulated_passive_tx_bytes": 1},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_099_group_d_authorization_claims_fail_closed(self) -> None:
        for kw in (
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                simulate_bench_dry_run=True, **kw
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    # ------------------------------------------------------------------
    # 8. Tier-0 Dual-Media Receipt, Report Verifier, Markdown & CLI (13)
    # ------------------------------------------------------------------

    def test_100_tier0_valid_dual_media_receipts_distinct_st_dev_pass(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        rep = evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertEqual(
            rep.go_no_go,
            P371_GO_NO_GO_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.live_attach_authorized)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertTrue(verify_phase371_report(rep).valid)

    def test_101_tier0_same_st_dev_rejected(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0x1001,
            st_dev_b_override=0x1001,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_102_tier0_single_copy_or_bad_size_or_corrupt_magic_rejected(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        gd_single = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        self.assertFalse(gd_single.passed)
        self._assert_err(gd_single, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        gd_size = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=b"SHORT",
            receipt_b_bytes=b"SHORT",
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        self.assertFalse(gd_size.passed)
        self._assert_err(gd_size, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        bad_rcpt = b"BADMAGIC" + sim["receipt_a_bytes"][8:]
        gd_corrupt = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=bad_rcpt,
            receipt_b_bytes=bad_rcpt,
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
        )
        self.assertFalse(gd_corrupt.passed)
        self._assert_err(gd_corrupt, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_103_tier0_trivial_serial_or_cid_rejected(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        for bad_ser in ("00000000", "BAD-SER"):
            gd = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=0x1001,
                st_dev_b_override=0x2002,
                body_serial=bad_ser,
                emmc_cid=sim["emmc_cid"],
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        gd_cid = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid="0" * 32,
        )
        self.assertFalse(gd_cid.passed)
        self._assert_err(gd_cid, P371_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_104_tier0_h0_h3_drift_and_missing_keys_rejected(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        gd_sim_drift = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(gd_sim_drift.passed)
        self._assert_err(gd_sim_drift, P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

        drifted_h3 = dict(sim["h3_baselines"])
        first_key = REQUIRED_H0_BASELINE_KEYS[0]
        drifted_h3[first_key] = "f" * 64
        gd_key_drift = evaluate_p371_check_group_d_creatorsapp_ble_g114_shotmark_and_tier0(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=0x1001,
            st_dev_b_override=0x2002,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=drifted_h3,
        )
        self.assertFalse(gd_key_drift.passed)
        self._assert_err(gd_key_drift, P371_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_105_verify_phase371_report_tamper_detection(self) -> None:
        rep = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        self.assertTrue(verify_phase371_report(d).valid)

        d_bad_sha = copy.deepcopy(d)
        d_bad_sha["check_groups_passed"] = 3
        res_sha = verify_phase371_report(d_bad_sha)
        self.assertFalse(res_sha.valid)

        d_bad_auth = copy.deepcopy(d)
        d_bad_auth["overall_ready_for_hardware_attach"] = True
        res_auth = verify_phase371_report(d_bad_auth)
        self.assertFalse(res_auth.valid)

        d_bad_zero = copy.deepcopy(d)
        d_bad_zero["rf_tx_packets"] = 1
        res_zero = verify_phase371_report(d_bad_zero)
        self.assertFalse(res_zero.valid)

    def test_106_render_phase371_markdown_contains_key_sections(self) -> None:
        rep = run_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase371_markdown(rep)
        self.assertIn("Phase 371", md)
        self.assertIn(P371_SCHEMA, md)
        self.assertIn(rep.report_sha256, md)
        self.assertIn(P371_CHECK_GROUP_A_ID, md)
        self.assertIn(P371_CHECK_GROUP_D_ID, md)

    def test_107_cli_help_percent_escaping_clean(self) -> None:
        cp = self._run_cli([CLI_CMD_ALIAS, "--help"])
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("709(800%)", cp.stdout)
        self.assertIn("--zoom-range", cp.stdout)
        self.assertIn("--airplane-mode", cp.stdout)

    def test_108_cli_offline_returns_rc2_and_valid_json(self) -> None:
        cp = self._run_cli([CLI_CMD_LONG, "--json"], clear_clean_room_env=True)
        self.assertEqual(cp.returncode, 2, msg=cp.stderr)
        payload = json.loads(cp.stdout)
        self.assertEqual(payload["schema_version"], P371_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(payload["check_groups_passed"], 4)
        self.assertFalse(payload["tier0_receipt_verified"])
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertTrue(verify_phase371_report(payload).valid)

    def test_109_cli_simulate_bench_dry_run_returns_rc0_and_alias_parity(self) -> None:
        cp_long = self._run_cli(
            [CLI_CMD_LONG, "--simulate-bench-dry-run", "--force-clean-room", "--json"]
        )
        cp_alias = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--force-clean-room", "--json"]
        )
        self.assertEqual(cp_long.returncode, 0, msg=cp_long.stderr)
        self.assertEqual(cp_alias.returncode, 0, msg=cp_alias.stderr)
        d_long = json.loads(cp_long.stdout)
        d_alias = json.loads(cp_alias.stdout)
        self.assertEqual(d_long["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(d_long["receipt_mode"], "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH")
        self.assertEqual(d_long["h0_equals_h3_count"], 16)
        self.assertFalse(d_long["overall_ready_for_hardware_attach"])
        self.assertEqual(d_long["report_sha256"], d_alias["report_sha256"])

    def test_110_cli_clean_room_env_modes_and_donorless_work_root_pass_dry_run(self) -> None:
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            cp = self._run_cli(
                [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
                env_overrides={env_key: "1"},
            )
            self.assertEqual(cp.returncode, 0, msg=f"{env_key}: {cp.stderr}")
            d = json.loads(cp.stdout)
            self.assertEqual(d["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(verify_phase371_report(d).valid)

        cp_missing = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
            clear_clean_room_env=True,
            env_overrides={"FX3_FX6_MAC_WORK_ROOT": "/nonexistent/phase371_cli_missing"},
        )
        self.assertEqual(cp_missing.returncode, 0, msg=cp_missing.stderr)
        d_miss = json.loads(cp_missing.stdout)
        self.assertIn(d_miss["verification_mode"], ("CLEAN_ROOM_SYNTHETIC", "LOCAL_DONOR_O_RDONLY"))
        self.assertTrue(verify_phase371_report(d_miss).valid)

        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            rep_dl = evaluate_realhw_zoomspeed_mydial3_hdmi4k_sdi12g_tcub_ftps_creatorsapp_ble_and_shotmark_preflight(
                simulate_bench_dry_run=True, force_clean_room=False
            )
        self.assertEqual(rep_dl.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_dl.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase371_report(rep_dl).valid)

    def test_111_cli_receipt_files_from_temp_files_verify_or_reject_same_fs(self) -> None:
        sim = build_simulated_phase371_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            ra = Path(td) / "receipt_a.bin"
            rb = Path(td) / "receipt_b.bin"
            ra.write_bytes(sim["receipt_a_bytes"])
            rb.write_bytes(sim["receipt_b_bytes"])
            cp = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--receipt-a",
                    str(ra),
                    "--receipt-b",
                    str(rb),
                    "--body-serial",
                    sim["body_serial"],
                    "--emmc-cid",
                    sim["emmc_cid"],
                    "--force-clean-room",
                    "--json",
                ]
            )
            # Same temp directory -> same st_dev -> fail-closed rc=2!
            self.assertEqual(cp.returncode, 2)
            d = json.loads(cp.stdout)
            self.assertEqual(
                d["go_no_go"],
                P371_GO_NO_GO_BLOCKED_ZOOMSPEED_MYDIAL3_HDMI4K_SDI12G_TCUB_FTPS_CREATORSAPP_BLE_AND_SHOTMARK_FAILURE,
            )

    def test_112_cli_output_json_and_markdown_out_written_with_failure_rc2_on_redline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "p371.json"
            out_md = Path(td) / "p371.md"
            cp_ok = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--simulate-bench-dry-run",
                    "--force-clean-room",
                    "--output",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                    "--summary",
                ]
            )
            self.assertEqual(cp_ok.returncode, 0, msg=cp_ok.stderr)
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", cp_ok.stdout)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(verify_phase371_report(json.loads(out_json.read_text())).valid)

            cp_fail = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--simulate-bench-dry-run",
                    "--force-clean-room",
                    "--claim-hardware-live-attach-authorized",
                    "--summary",
                ]
            )
            self.assertEqual(cp_fail.returncode, 2)


if __name__ == "__main__":
    unittest.main()
