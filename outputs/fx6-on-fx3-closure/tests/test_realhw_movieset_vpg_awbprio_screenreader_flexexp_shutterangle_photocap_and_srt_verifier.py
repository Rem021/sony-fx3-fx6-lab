"""Four-mode unit tests (108 cases) for Phase 368
(`preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt`
+ short alias `preflight-phase368`):
23rd Physical Bench Readiness Verifier across Global Sony Waves 77-78 check groups (`A..D`):
- Group A (Waves 77.1 & 77.2):
  - `[File Format]` 6-codec matrix (`XAVC HS 4K` without `29.97p/25p`, `XAVC S-I DCI 4K`
    `24.00p` `MODEL_EVENT_REBOOT_BY_CROSS_2400P` & playback isolation, S&Q `60/50fps` cap &
    `48fps` exclusivity), `G139` errata (`S&Q XAVC S HD 100/120fps` requires only `V60+`;
    `200/240fps` requires `V90`), 5-tier `100..1350MBPS` `VPG400` proxy threshold
    (`0xea64/0xea6c/0xea78/0xea7b`), dormant `xavc_hs_8k` (`EOPNOTSUPP=95`), FX6 `Class300`
    & dormant `Class480`/`XAVC-L25`.
  - `[Priority Set in AWB]` (Resettable, ineffective in `Cine EI`) vs Still-only
    Reset-resistant `[Shutter AWB Lock]` (`_f 0x66db`, Movie uses Custom Key), `2500..9900K`
    `75`-step Kelvin (`29` A-B / `57` G-M) vs FX6 `B/A/PRESET`, `2000..15000K`, `ATW Speed 1..5`.
- Group B (Waves 77.3 & 77.4):
  - `G109` errata reconciliation: ALL 4 `[Focus Assistant]` items & ALL 3 `[Peaking Display]`
    items (`0 px` HDMI) resist `[Camera Settings Reset]` (`Initialize`-only); Still-only
    `[AF in Focus Mag.]` 5-lockout matrix; 4-item Reset-resistant `[Touch Operation]` vs
    dormant `[Touch Panel/Pad]`/`[Touch Shutter]` (`0` UI items); FX6 3-item `Peaking` vs
    dormant `Normal`/`Frequency`.
  - Dual-model compiled-but-SKU-gated `[Accessibility]`/`[Screen Reader]` (`0` UI items on
    both FX3 & FX6, `0` HDMI hits); `G104` errata exact 2-row `[Version]` (`Body` + `Lens`
    shared Mount-Adaptor slot, `0` MI-Shoe version); Airplane Mode silences red update dot;
    `Slot 1 BODYDATA.DAT` blocked `EROFS=30`.
- Group C (Waves 78.1 & 78.2):
  - `G86` gap closure: Reset-resistant parent `[Exposure Ctrl Type]` vs Resettable
    `[Auto/Manual Swt. Set.]` & `[Auto Slow Shutter]`; Movie/S&Q `[Shutter Mode]` `Speed`/
    `Angle` (`19` std degrees + `10` slow frames `2F..64F`), `BK4` `0x01120024` vs
    `0x01120028` independent registers, `[Exposure step]` immunity, forced Still/Movie split,
    Still-only `[Anti-flicker Shoot.]`, dormant `Var. Shutter` disproof, FX6 4-mode shutter.
  - `[SteadyShot]` `Active` (`~1.104x` crop) 4-lockout matrix (`119.88p/100p`, `S&Q>=100fps`,
    `HDMI RAW=On`, `De-Squeeze!=Off`), Ver. 2.00+ removal of `>=200mm` note, exact `47`-entry
    `8..1000mm` table, dormant `Dynamic/Intelligent/Super Active`, `Catalyst` Gyro `RTMD`
    `Off/Active`-only & `120p`/`S&Q`/HDMI dropout; FX6 zero body IBIS + 3-step lens OSS.
- Group D + Tier-0 (Waves 78.3 & 78.4 + Tier-0):
  - `Playback -> [Photo Capture]` `8.3M`/`2.1M` (`DCI 4K` blocked, Reset-resistant Playback
    `[JPEG/HEIF Switch]`), `G126` exact 3-item `[View Mode]` (`Date View`/`Folder View(Still)`/
    `Movie View`, dormant `AVCHD`/`MP4` rejected), `[Rating]` `0..5` & `Slot 1 EROFS=30`,
    FX6 `0` Photo Capture + `Clip Flag` `OK/NG/KEEP`.
  - Zero native UVC `[USB Streaming]` (`4K 30p` rumor disproved, exact 4 USB connection modes),
    outbound-only `SRT Caller` (`0 SRT Listener`, rejects `:port`/`?streamid=`), `38 Mbps` /
    no-`24p`/`120p`, `Creators' App` BT gate, `Airplane Mode=On` Zero-RF surviving
    `[Reset Network Set.]` & `USB-LAN` bypass, FX6 external `CBK-WA100/PDT-FP1`; plus
    `16/16 H0 == H3` dual-media `528 B FX3RCPT1` Tier-0 gate and hard-locked
    `ready_for_live_camera_attach=False`.

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
)
from fx6_closure.realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier import (  # noqa: E402
    P368_AWB_PRIORITY_MODES,
    P368_BK4_SHUTTER_ANGLE_REG,
    P368_BK4_SHUTTER_SPEED_REG,
    P368_BOUNDED_DONOR_PATHS,
    P368_CHECK_GROUP_A_ID,
    P368_CHECK_GROUP_B_ID,
    P368_CHECK_GROUP_C_ID,
    P368_CHECK_GROUP_D_ID,
    P368_DORMANT_STEADYSHOT_MODES,
    P368_DORMANT_TOUCH_ITEMS,
    P368_ERRNO_EOPNOTSUPP,
    P368_ERRNO_EROFS,
    P368_EXPOSURE_CTRL_TYPES,
    P368_FOCUS_ASSISTANT_EXACT_4_ITEMS,
    P368_FX3_ACTIVE_FILE_FORMATS,
    P368_FX3_DORMANT_FILE_FORMATS,
    P368_FX3_DORMANT_UVC_FORMATS,
    P368_FX3_SCREEN_READER_HDMI_HITS,
    P368_FX3_SCREEN_READER_UI_COUNT,
    P368_FX3_UVC_STREAMING_SUPPORTED,
    P368_FX3_VAR_SHUTTER_UI_COUNT,
    P368_FX3_VERSION_EXACT_2_ROWS,
    P368_FX6_ATW_SPEED_MAX,
    P368_FX6_ATW_SPEED_MIN,
    P368_FX6_BODY_IBIS_COUNT,
    P368_FX6_BUILTIN_STREAMING_COUNT,
    P368_FX6_CLIP_FLAGS,
    P368_FX6_DORMANT_REC_FORMATS,
    P368_FX6_EXTERNAL_STREAMING_ADAPTERS,
    P368_FX6_FOCUS_MAG_HDMI_RATIO,
    P368_FX6_FOCUS_MAG_VF_RATIO,
    P368_FX6_IBIS_UNSUPPORTED_SYMBOL,
    P368_FX6_KELVIN_MAX_K,
    P368_FX6_KELVIN_MIN_K,
    P368_FX6_LENS_OSS_MODES,
    P368_FX6_NATIVE_UVC_COUNT,
    P368_FX6_PEAKING_DORMANT_BINDINGS,
    P368_FX6_PEAKING_EXACT_3_ITEMS,
    P368_FX6_PHOTO_CAPTURE_UI_COUNT,
    P368_FX6_REC_FORMAT_CODECS,
    P368_FX6_SCREEN_READER_UI_COUNT,
    P368_FX6_SHUTTER_MODES,
    P368_FX6_VERSION_ROWS,
    P368_FX6_WHT_BAL_SWITCH_POSITIONS,
    P368_FX6_XAVC_I_MAX_CLASS,
    P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN,
    P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400,
    P368_GA_ERR_FX6_ATW_OR_WHT_BAL,
    P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300,
    P368_GA_ERR_MODEL_OR_FW_FLOOR,
    P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION,
    P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET,
    P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG,
    P368_GB_ERR_SCREEN_READER_SKU_GATE,
    P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD,
    P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30,
    P368_GC_ERR_FLEX_EXP_G86_RESET_SPLIT,
    P368_GC_ERR_FX6_4MODE_SHUTTER_CONTRACT,
    P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS,
    P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER,
    P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST,
    P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF,
    P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET,
    P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF,
    P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30,
    P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE,
    P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED,
    P368_HEADER_READ_BYTES,
    P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM,
    P368_KELVIN_MAX_K,
    P368_KELVIN_MIN_K,
    P368_KELVIN_STEP_COUNT,
    P368_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P368_PB_JPEG_HEIF_MODES,
    P368_PEAKING_EXACT_3_ITEMS,
    P368_PEAKING_HDMI_PIXEL_COUNT,
    P368_PHOTO_CAPTURE_4K_MP,
    P368_PHOTO_CAPTURE_HD_MP,
    P368_REBOOT_2400P_EVENT,
    P368_SCHEMA,
    P368_SHUTTER_ANGLE_SLOW_FRAMES,
    P368_SHUTTER_ANGLE_STANDARD_DEGREES,
    P368_SHUTTER_AWB_LOCK_MODES,
    P368_SHUTTER_MODES,
    P368_SONY_HELP_GUIDE_ID,
    P368_SRT_EXPOSED_ROLES,
    P368_STEADYSHOT_ACTIVE_CROP_FACTOR,
    P368_STEADYSHOT_MOVIE_MODES,
    P368_STREAMING_ALLOWED_FPS,
    P368_STREAMING_BLOCKED_FPS,
    P368_STREAMING_MAX_BITRATE_MBPS,
    P368_STREAMING_PROFILES,
    P368_STREAMING_PROTOCOLS,
    P368_TOUCH_OPERATION_EXACT_4_ITEMS,
    P368_USB_CONNECTION_EXACT_4_MODES,
    P368_VALID_MEDIA_CARD_SPEEDS,
    P368_VERSION,
    P368_VIEW_MODE_DORMANT_ITEMS,
    P368_VIEW_MODE_EXACT_3_ITEMS,
    P368_VPG400_UXC_RESIDS,
    build_simulated_phase368_tier0_receipts,
    evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw,
    evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version,
    evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst,
    evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0,
    evaluate_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight,
    inspect_phase368_donors_bounded,
    render_phase368_markdown,
    run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight,
    verify_phase368_report,
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
    "fx6_closure.realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_verifier"
)
CLI_CMD_LONG = "preflight-movieset-vpg-awbprio-screenreader-flexexp-shutterangle-photocap-and-srt"
CLI_CMD_ALIAS = "preflight-phase368"


class TestPhase368Preflight23Verifier(unittest.TestCase):
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
            timeout=45,
        )

    # ------------------------------------------------------------------
    # 1. Exports, Zero Shadowing & Bounded O_RDONLY / 4-Mode Parity
    # ------------------------------------------------------------------

    def test_001_package_exports_and_all_contain_phase368_symbols(self) -> None:
        required = (
            "P368_SCHEMA",
            "P368_VERSION",
            "evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw",
            "evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version",
            "evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst",
            "evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0",
            "evaluate_realhw_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight",
            "run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight",
            "verify_phase368_report",
            "render_phase368_markdown",
            "build_simulated_phase368_tier0_receipts",
            "inspect_phase368_donors_bounded",
            "RealHwMovieSetVpgAwbPrioScreenReaderFlexExpShutterAnglePhotoCapAndSrtReport",
        )
        for sym in required:
            self.assertTrue(hasattr(fx6_closure, sym), msg=f"Missing export {sym}")
            self.assertIn(sym, fx6_closure.__all__, msg=f"Missing __all__ entry {sym}")

    def test_002_no_shadowing_of_phase358_and_milestone364_exports(self) -> None:
        self.assertNotEqual(fx6_closure.P358_SCHEMA, fx6_closure.P368_SCHEMA)
        self.assertEqual(fx6_closure.P368_SCHEMA, P368_SCHEMA)
        self.assertEqual(fx6_closure.P368_VERSION, P368_VERSION)
        self.assertTrue(hasattr(fx6_closure, "evaluate_milestone_364_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "verify_milestone_364_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "verify_phase358_report"))

    def test_003_bounded_donor_paths_count_and_header_size(self) -> None:
        self.assertEqual(len(P368_BOUNDED_DONOR_PATHS), 8)
        self.assertEqual(P368_HEADER_READ_BYTES, 64)
        self.assertEqual(P368_SONY_HELP_GUIDE_ID, "ilc/2210")

    def test_004_donor_inspection_force_clean_room_and_env_variants(self) -> None:
        d_flag = inspect_phase368_donors_bounded(force_clean_room=True)
        self.assertEqual(d_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(d_flag.donor_tree_present)
        self.assertEqual(d_flag.bytes_read_total, 0)
        self.assertEqual(d_flag.raw_firmware_bytes_leaked, 0)

        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            d_env1 = inspect_phase368_donors_bounded()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            d_env2 = inspect_phase368_donors_bounded()
        self.assertEqual(d_env1.header_digests, d_flag.header_digests)
        self.assertEqual(d_env2.header_digests, d_flag.header_digests)

    def test_005_donor_inspection_mocked_work_root_none_synthetic(self) -> None:
        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            d = inspect_phase368_donors_bounded(force_clean_room=False)
        self.assertEqual(d.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(d.donor_tree_present)
        self.assertEqual(d.bytes_read_total, 0)
        self.assertEqual(d.raw_firmware_bytes_leaked, 0)

    def test_006_donor_inspection_nonexistent_work_root_fallback(self) -> None:
        d = inspect_phase368_donors_bounded(
            force_clean_room=False,
            work_root=Path("/nonexistent/phase368_missing_donor_root"),
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
            (fx3_dir / "libInfraSrtLiveStreaming.so").write_bytes(b"SRT_ELF_" + b"C" * 512)
            with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
                d = inspect_phase368_donors_bounded(
                    force_clean_room=False,
                    fx6_lib_dir=fx6_dir,
                    fx3_modules_dir=fx3_dir,
                )
            self.assertEqual(d.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(d.donor_tree_present)
            self.assertGreaterEqual(d.donors_present, 3)
            self.assertEqual(d.bytes_read_total, d.donors_present * 64)
            self.assertEqual(d.raw_firmware_bytes_leaked, 0)

    def test_008_timing_stripping_removes_elapsed_fields_from_sha256(self) -> None:
        rep_a = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        rep_b = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep_a.report_sha256, rep_b.report_sha256)
        payload = rep_a.to_dict()
        payload["donor_inspection"]["elapsed_seconds"] = 99.123456
        self.assertTrue(verify_phase368_report(payload).valid)

    # ------------------------------------------------------------------
    # 2. Wave 77.1 (Group A): 6-Codec Matrix, 24.00p, G139 & VPG400
    # ------------------------------------------------------------------

    def test_009_wave77_1_all_6_active_fx3_file_formats_supported(self) -> None:
        self.assertEqual(len(P368_FX3_ACTIVE_FILE_FORMATS), 6)
        for fmt in P368_FX3_ACTIVE_FILE_FORMATS:
            fps = 24.0 if fmt == "XAVC_S_I_DCI_4K" else 59.94
            prev_fps = 24.0 if fmt == "XAVC_S_I_DCI_4K" else 59.94
            ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                file_format=fmt,
                rec_frame_rate_fps=fps,
                prev_rec_frame_rate_fps=prev_fps,
                playback_clip_fps=fps,
                media_card_speed="CFEA_VPG400",
            )
            self.assertTrue(ga.passed, msg=f"{fmt} failed: {ga.errors}")

    def test_010_wave77_1_xavc_hs_4k_rejects_29_97p_and_25p(self) -> None:
        for bad_fps in (29.97, 25.0):
            ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                file_format="XAVC_HS_4K", rec_frame_rate_fps=bad_fps
            )
            self.assertFalse(ga.passed)
            self._assert_err(ga, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        ga_claim = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            expect_xavc_hs_4k_has_29_97p_or_25p=True
        )
        self.assertFalse(ga_claim.passed)
        self._assert_err(ga_claim, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

    def test_011_wave77_1_2400p_exclusive_to_dci4k_and_triggers_reboot_flag(self) -> None:
        ga_bad = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_I_4K", rec_frame_rate_fps=24.0
        )
        self.assertFalse(ga_bad.passed)
        self._assert_err(ga_bad, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        ga_ok = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_I_DCI_4K",
            rec_frame_rate_fps=24.0,
            prev_rec_frame_rate_fps=59.94,
            playback_clip_fps=24.0,
        )
        self.assertTrue(ga_ok.passed)
        self.assertTrue(ga_ok.cross_2400p_reboot_triggered)
        self.assertTrue(ga_ok.playback_2400p_isolated)
        self.assertEqual(P368_REBOOT_2400P_EVENT, "MODEL_EVENT_REBOOT_BY_CROSS_2400P")

    def test_012_wave77_1_cross_2400p_without_reboot_or_mixed_playback_rejected(self) -> None:
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            expect_cross_2400p_without_reboot_or_mixed_playback=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        ga_warn = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_I_DCI_4K",
            rec_frame_rate_fps=24.0,
            playback_clip_fps=59.94,
        )
        self.assertTrue(ga_warn.passed)
        self.assertTrue(any("24.00p playback isolation" in w for w in ga_warn.warnings))

    def test_013_wave77_1_g139_erratum_sq_xavc_s_hd_100_120fps_requires_only_v60(self) -> None:
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_HD",
            sq_frame_rate_fps=120,
            media_card_speed="SDXC_V60",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.required_min_card_speed, "SDXC_V60")

        ga_v30 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_HD",
            sq_frame_rate_fps=120,
            media_card_speed="SDXC_U3_V30",
        )
        self.assertFalse(ga_v30.passed)
        self._assert_err(ga_v30, P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400)

        ga_claim_v90 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            expect_sq_xavc_s_hd_120fps_requires_v90=True
        )
        self.assertFalse(ga_claim_v90.passed)
        self._assert_err(ga_claim_v90, P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400)

    def test_014_wave77_1_sq_xavc_s_hd_200_240fps_requires_v90(self) -> None:
        ga_v60 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_HD",
            sq_frame_rate_fps=240,
            media_card_speed="SDXC_V60",
        )
        self.assertFalse(ga_v60.passed)
        self._assert_err(ga_v60, P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400)

        ga_v90 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_HD",
            sq_frame_rate_fps=240,
            media_card_speed="SDXC_V90",
        )
        self.assertTrue(ga_v90.passed)
        self.assertEqual(ga_v90.required_min_card_speed, "SDXC_V90")

    def test_015_wave77_1_dci4k_sq_caps_at_60fps_and_48fps_exclusive_to_2400p(self) -> None:
        ga_120 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_DCI_4K",
            rec_frame_rate_fps=24.0,
            sq_frame_rate_fps=120,
        )
        self.assertFalse(ga_120.passed)
        self._assert_err(ga_120, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        ga_48_ok = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_DCI_4K",
            rec_frame_rate_fps=24.0,
            sq_frame_rate_fps=48,
        )
        self.assertTrue(ga_48_ok.passed)

        ga_48_bad = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_4K",
            rec_frame_rate_fps=23.98,
            sq_frame_rate_fps=48,
        )
        self.assertFalse(ga_48_bad.passed)
        self._assert_err(ga_48_bad, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                expect_sq_dci4k_allows_100_or_120fps=True
            ).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                expect_sq_48fps_outside_dci4k_2400p=True
            ).passed
        )

    def test_016_wave77_1_vpg400_proxy_1350mbps_firewall_and_uxc_resids(self) -> None:
        self.assertEqual(P368_VPG400_UXC_RESIDS, ("0xea64", "0xea6c", "0xea78", "0xea7b"))
        ga_vpg200 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_4K",
            sq_frame_rate_fps=120,
            record_setting_mbps=1200,
            proxy_recording_enabled=True,
            media_card_speed="CFEA_VPG200",
        )
        self.assertFalse(ga_vpg200.passed)
        self.assertTrue(ga_vpg200.vpg400_proxy_threshold_triggered)
        self.assertEqual(ga_vpg200.required_min_card_speed, "CFEA_VPG400")
        self._assert_err(ga_vpg200, P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400)

        ga_vpg400 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_4K",
            sq_frame_rate_fps=120,
            record_setting_mbps=1200,
            proxy_recording_enabled=True,
            media_card_speed="CFEA_VPG400",
        )
        self.assertTrue(ga_vpg400.passed)
        self.assertTrue(ga_vpg400.vpg400_proxy_threshold_triggered)

        ga_claim = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            expect_high_rate_sq_proxy_succeeds_without_vpg400=True
        )
        self.assertFalse(ga_claim.passed)

    def test_017_wave77_1_dormant_8k_and_movie_settings_reset_behavior(self) -> None:
        self.assertEqual(P368_FX3_DORMANT_FILE_FORMATS, ("XAVC_HS_8K",))
        ga_8k = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            dormant_file_format_requested="XAVC_HS_8K"
        )
        self.assertFalse(ga_8k.passed)
        self._assert_err(ga_8k, P368_GA_ERR_MOVIESET_CODEC_OR_24P_ISOLATION)

        ga_rst = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_I_4K",
            reset_action="CAMERA_SETTINGS_RESET",
        )
        self.assertTrue(ga_rst.passed)
        self.assertEqual(ga_rst.effective_file_format_after_reset, "XAVC_S_HD")
        self.assertEqual(ga_rst.fx3_dormant_8k_ui_count, 0)

        ga_claim_rst = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            claimed_movie_settings_resist_camera_reset=True
        )
        self.assertFalse(ga_claim_rst.passed)

    def test_018_wave77_1_fx6_class300_xavc_l_no_dci4k_and_dormant_class480(self) -> None:
        self.assertEqual(P368_FX6_XAVC_I_MAX_CLASS, "CLASS300")
        self.assertEqual(P368_FX6_DORMANT_REC_FORMATS, ("CLASS480", "XAVC_L25"))
        for codec in P368_FX6_REC_FORMAT_CODECS:
            vid = "3840x2160" if codec == "XAVC_L" else "4096x2160"
            self.assertTrue(
                evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                    fx6_rec_codec=codec, fx6_video_format=vid
                ).passed
            )

        ga_bad_l = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            fx6_rec_codec="XAVC_L", fx6_video_format="4096x2160"
        )
        self.assertFalse(ga_bad_l.passed)
        self._assert_err(ga_bad_l, P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300)

        ga_dorm = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            fx6_dormant_rec_format_requested="CLASS480"
        )
        self.assertFalse(ga_dorm.passed)
        self._assert_err(ga_dorm, P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300)

        ga_mbps = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(fx6_rec_mbps=960)
        self.assertFalse(ga_mbps.passed)
        self._assert_err(ga_mbps, P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300)

    # ------------------------------------------------------------------
    # 3. Wave 77.2 (Group A): Priority Set in AWB, Shutter AWB Lock, 75-Step K & FX6 ATW
    # ------------------------------------------------------------------

    def test_019_wave77_2_awb_priority_resettable_and_ineffective_in_cine_ei(self) -> None:
        for mode in P368_AWB_PRIORITY_MODES:
            ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                awb_priority_set=mode, reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(ga.passed)
            self.assertEqual(ga.effective_awb_priority_after_reset, "STANDARD")
            self.assertTrue(ga.awb_priority_effective_in_log)

        ga_cei = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            log_shooting_mode="CINE_EI"
        )
        self.assertTrue(ga_cei.passed)
        self.assertFalse(ga_cei.awb_priority_effective_in_log)

        ga_cei_bad = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            log_shooting_mode="CINE_EI_QUICK",
            expect_awb_priority_effective_in_cine_ei=True,
        )
        self.assertFalse(ga_cei_bad.passed)
        self._assert_err(ga_cei_bad, P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN)

    def test_020_wave77_2_shutter_awb_lock_still_only_and_resists_camera_reset(self) -> None:
        for mode in P368_SHUTTER_AWB_LOCK_MODES:
            ga_cam_rst = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                shutter_awb_lock=mode, reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(ga_cam_rst.passed)
            self.assertEqual(ga_cam_rst.effective_shutter_awb_lock_after_reset, mode)
            self.assertTrue(ga_cam_rst.shutter_awb_lock_still_only)
            self.assertTrue(ga_cam_rst.shutter_awb_lock_resists_camera_reset)

            ga_init = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                shutter_awb_lock=mode, reset_action="INITIALIZE"
            )
            self.assertTrue(ga_init.passed)
            self.assertEqual(ga_init.effective_shutter_awb_lock_after_reset, "OFF")

        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                expect_shutter_awb_lock_active_in_movie=True
            ).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                claimed_shutter_awb_lock_wiped_by_camera_reset=True
            ).passed
        )

    def test_021_wave77_2_kelvin_75_steps_2500_to_9900k_and_tint_axes(self) -> None:
        self.assertEqual(P368_KELVIN_MIN_K, 2500)
        self.assertEqual(P368_KELVIN_MAX_K, 9900)
        self.assertEqual(P368_KELVIN_STEP_COUNT, 75)
        self.assertTrue(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(kelvin_temp_k=2500).passed
        )
        self.assertTrue(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(kelvin_temp_k=9900).passed
        )
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(kelvin_temp_k=5650)
        self.assertFalse(ga.passed)
        self._assert_err(ga, P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN)
        ga_hi = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(kelvin_temp_k=10500)
        self.assertFalse(ga_hi.passed)

    def test_022_wave77_2_fx6_wht_bal_switch_and_atw_speed_1_to_5(self) -> None:
        self.assertEqual(P368_FX6_KELVIN_MIN_K, 2000)
        self.assertEqual(P368_FX6_KELVIN_MAX_K, 15000)
        for sw in P368_FX6_WHT_BAL_SWITCH_POSITIONS:
            for spd in range(P368_FX6_ATW_SPEED_MIN, P368_FX6_ATW_SPEED_MAX + 1):
                ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                    fx6_wht_bal_switch=sw, fx6_atw_speed=spd, fx6_kelvin_temp_k=15000
                )
                self.assertTrue(ga.passed)
        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(fx6_atw_speed=6).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                fx6_cine_ei_active=True, expect_fx6_atw_active_in_cine_ei=True
            ).passed
        )

    # ------------------------------------------------------------------
    # 4. Wave 77.3 (Group B): G109 Reset Errata, Touch Operation & FX6 Peaking
    # ------------------------------------------------------------------

    def test_023_wave77_3_g109_errata_focus_assist_4_and_peaking_3_resist_camera_reset(self) -> None:
        self.assertEqual(len(P368_FOCUS_ASSISTANT_EXACT_4_ITEMS), 4)
        self.assertEqual(len(P368_PEAKING_EXACT_3_ITEMS), 3)
        self.assertEqual(P368_PEAKING_HDMI_PIXEL_COUNT, 0)

        gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            reset_action="CAMERA_SETTINGS_RESET",
            peaking_display="ON",
            peaking_color="YELLOW",
        )
        self.assertTrue(gb.passed)
        self.assertTrue(gb.focus_assist_and_peaking_resist_camera_reset)
        self.assertEqual(gb.peaking_hdmi_pixel_count, 0)

        gb_bad = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            claimed_focus_assist_or_peaking_wiped_by_camera_reset=True
        )
        self.assertFalse(gb_bad.passed)
        self._assert_err(gb_bad, P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET)

        gb_hdmi = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            claimed_peaking_outputs_over_hdmi=True
        )
        self.assertFalse(gb_hdmi.passed)
        self._assert_err(gb_hdmi, P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET)

    def test_024_wave77_3_af_in_focus_mag_still_only_and_5_lockouts(self) -> None:
        gb_still = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            shoot_mode="PHOTO",
            focus_mode="MF",
            exposure_mode="MANUAL_EXPOSURE",
            initial_focus_mag="X2_1",
            af_in_focus_mag="ON",
        )
        self.assertTrue(gb_still.passed)
        self.assertTrue(gb_still.af_in_focus_mag_effective)

        for kwargs in (
            {"shoot_mode": "MOVIE"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_A", "exposure_mode": "SCENE"},
            {"shoot_mode": "PHOTO", "cont_shooting_active": True},
            {"shoot_mode": "PHOTO", "mount_adaptor_attached": True},
        ):
            gb_lock = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                expect_af_in_focus_mag_active_under_lockout=True,
                **kwargs,
            )
            self.assertFalse(gb_lock.passed)
            self._assert_err(gb_lock, P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET)

    def test_025_wave77_3_touch_operation_4_items_vs_dormant_touchpad_and_touch_shutter(self) -> None:
        self.assertEqual(len(P368_TOUCH_OPERATION_EXACT_4_ITEMS), 4)
        self.assertEqual(len(P368_DORMANT_TOUCH_ITEMS), 4)
        gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version()
        self.assertTrue(gb.passed)
        self.assertEqual(gb.fx3_dormant_touchpad_ui_count, 0)

        for dorm in P368_DORMANT_TOUCH_ITEMS:
            gb_dorm = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                dormant_touch_item_requested=dorm
            )
            self.assertFalse(gb_dorm.passed)
            self._assert_err(gb_dorm, P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD)

        self.assertFalse(
            evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                claimed_touch_operation_wiped_by_camera_reset=True
            ).passed
        )

    def test_026_wave77_3_fx6_peaking_3_items_vs_dormant_frequency_normal(self) -> None:
        self.assertEqual(P368_FX6_PEAKING_EXACT_3_ITEMS, ("Setting", "Peaking Level", "Color"))
        self.assertEqual(P368_FX6_FOCUS_MAG_VF_RATIO, "x3/x6")
        self.assertEqual(P368_FX6_FOCUS_MAG_HDMI_RATIO, "x2/x4")
        for dorm in P368_FX6_PEAKING_DORMANT_BINDINGS:
            gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                fx6_peaking_dormant_binding_requested=dorm
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG)

    # ------------------------------------------------------------------
    # 5. Wave 77.4 (Group B): Dual-Model Screen Reader Gate, G104 Version & BODYDATA
    # ------------------------------------------------------------------

    def test_027_wave77_4_screen_reader_compiled_but_sku_gated_on_fx3_and_fx6(self) -> None:
        self.assertEqual(P368_FX3_SCREEN_READER_UI_COUNT, 0)
        self.assertEqual(P368_FX6_SCREEN_READER_UI_COUNT, 0)
        self.assertEqual(P368_FX3_SCREEN_READER_HDMI_HITS, 0)

        for kwargs in (
            {"fx3_screen_reader_requested": True},
            {"fx6_screen_reader_requested": True},
            {"expect_screen_reader_outputs_over_hdmi": True},
        ):
            gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                **kwargs
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P368_GB_ERR_SCREEN_READER_SKU_GATE)

    def test_028_wave77_4_version_g104_erratum_exact_2_rows_and_bodydata_erofs30(self) -> None:
        self.assertEqual(P368_FX3_VERSION_EXACT_2_ROWS, ("Body", "Lens"))
        self.assertEqual(P368_FX6_VERSION_ROWS, ("Body", "Lens", "Ext. Unit"))

        gb_ok = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            mount_adaptor_fw_checked=True, airplane_mode="ON"
        )
        self.assertTrue(gb_ok.passed)
        self.assertTrue(gb_ok.mount_adaptor_shares_lens_slot)
        self.assertFalse(gb_ok.fx3_version_mi_shoe_shown)
        self.assertTrue(gb_ok.version_update_red_dot_silenced)
        self.assertTrue(gb_ok.bodydata_slot1_update_blocked_erofs30)

        for kwargs in (
            {"version_rows_exposed": ("Body", "Lens", "Mount Adaptor")},
            {"claimed_mount_adaptor_has_3rd_version_row": True},
            {"claimed_mi_shoe_version_shown": True},
            {"expect_update_red_dot_visible_in_airplane_mode": True},
            {"bodydata_slot1_flash_requested": True},
        ):
            gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                **kwargs
            )
            self.assertFalse(gb.passed)
            self._assert_err(gb, P368_GB_ERR_VERSION_2ROW_G104_OR_BODYDATA_EROFS30)

    # ------------------------------------------------------------------
    # 6. Wave 78.1 (Group C): G86 FlexExp Split, Shutter Mode/Angle, BK4 & FX6
    # ------------------------------------------------------------------

    def test_029_wave78_1_g86_gap_closure_parent_exposure_ctrl_type_resists_camera_reset(self) -> None:
        self.assertEqual(P368_EXPOSURE_CTRL_TYPES, ("FLEXIBLE_EXP_MODE", "PASM_MODE"))
        gc_rst = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            exposure_ctrl_type="PASM_MODE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gc_rst.passed)
        self.assertTrue(gc_rst.exposure_ctrl_type_resists_camera_reset)
        self.assertEqual(gc_rst.effective_exposure_ctrl_type_after_reset, "PASM_MODE")

        gc_init = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            exposure_ctrl_type="PASM_MODE", reset_action="INITIALIZE"
        )
        self.assertTrue(gc_init.passed)
        self.assertEqual(gc_init.effective_exposure_ctrl_type_after_reset, "FLEXIBLE_EXP_MODE")

        self.assertFalse(
            evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                claimed_exposure_ctrl_type_wiped_by_camera_reset=True
            ).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                claimed_auto_manual_or_slow_shutter_resists_reset=True
            ).passed
        )

    def test_030_wave78_1_shutter_mode_angle_enum_slow_frame_clamp_and_bk4_regs(self) -> None:
        self.assertEqual(len(P368_SHUTTER_ANGLE_STANDARD_DEGREES), 19)
        self.assertEqual(len(P368_SHUTTER_ANGLE_SLOW_FRAMES), 10)
        self.assertEqual(P368_BK4_SHUTTER_SPEED_REG, "0x01120024")
        self.assertEqual(P368_BK4_SHUTTER_ANGLE_REG, "0x01120028")

        for deg in P368_SHUTTER_ANGLE_STANDARD_DEGREES:
            gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                shutter_mode="ANGLE", shutter_angle_value=deg
            )
            self.assertTrue(gc.passed)
            self.assertTrue(gc.bk4_registers_independent)
            self.assertFalse(gc.exposure_step_affects_shutter_angle)
            self.assertTrue(gc.shutter_angle_splits_still_movie)

        gc_slow_ok = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            shutter_mode="ANGLE", shutter_angle_value="8F", frame_rate_fps=23.98
        )
        self.assertTrue(gc_slow_ok.passed)

        gc_slow_bad = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            shutter_mode="ANGLE", shutter_angle_value="8F", frame_rate_fps=119.88
        )
        self.assertFalse(gc_slow_bad.passed)
        self._assert_err(gc_slow_bad, P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER)

    def test_031_wave78_1_shutter_angle_myths_var_shutter_dormant_and_fx6_4mode(self) -> None:
        self.assertEqual(P368_FX3_VAR_SHUTTER_UI_COUNT, 0)
        self.assertEqual(P368_FX6_SHUTTER_MODES, ("ANGLE", "SPEED", "ECS", "OFF"))

        for kwargs in (
            {"expect_shutter_angle_active_in_still": True},
            {"expect_exposure_step_alters_shutter_angle": True},
            {"claimed_shutter_angle_shared_when_diffset_unchecked": True},
            {"claimed_bk4_speed_and_angle_overwrite_each_other": True},
            {"expect_anti_flicker_active_in_movie": True},
            {"dormant_var_shutter_requested": True},
        ):
            gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(**kwargs)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P368_GC_ERR_SHUTTER_MODE_ANGLE_BK4_OR_VAR_SHUTTER)

        for fx6_mode in P368_FX6_SHUTTER_MODES:
            self.assertTrue(
                evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                    fx6_shutter_mode=fx6_mode
                ).passed
            )
        gc_fx6_bad = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            fx6_shutter_mode="VAR_SHUTTER"
        )
        self.assertFalse(gc_fx6_bad.passed)
        self._assert_err(gc_fx6_bad, P368_GC_ERR_FX6_4MODE_SHUTTER_CONTRACT)

    # ------------------------------------------------------------------
    # 7. Wave 78.2 (Group C): SteadyShot Active 4-Lockout, Catalyst RTMD & FX6 OSS
    # ------------------------------------------------------------------

    def test_032_wave78_2_steadyshot_active_4_lockout_matrix(self) -> None:
        self.assertAlmostEqual(P368_STEADYSHOT_ACTIVE_CROP_FACTOR, 1.104)
        gc_ok = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            steadyshot_movie="ACTIVE", frame_rate_fps=23.98, hdmi_raw_output=False, desqueeze_display="OFF"
        )
        self.assertTrue(gc_ok.passed)
        self.assertEqual(gc_ok.effective_steadyshot_movie, "ACTIVE")
        self.assertFalse(gc_ok.steadyshot_active_locked_out)
        self.assertTrue(gc_ok.catalyst_gyro_rtmd_available)

        for kwargs in (
            {"frame_rate_fps": 119.88},
            {"shoot_mode": "S_AND_Q", "sq_frame_rate_fps": 120},
            {"hdmi_raw_output": True},
            {"desqueeze_display": "1.3X"},
        ):
            gc_fb = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                steadyshot_movie="ACTIVE", **kwargs
            )
            self.assertTrue(gc_fb.passed)
            self.assertTrue(gc_fb.steadyshot_active_locked_out)
            self.assertEqual(gc_fb.effective_steadyshot_movie, "STANDARD")

            gc_bad = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                steadyshot_movie="ACTIVE",
                expect_steadyshot_active_under_lockout=True,
                **kwargs,
            )
            self.assertFalse(gc_bad.passed)
            self._assert_err(gc_bad, P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST)

    def test_033_wave78_2_catalyst_gyro_rtmd_dropout_and_47_focal_table(self) -> None:
        self.assertEqual(len(P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM), 47)
        self.assertEqual(P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM[0], 8)
        self.assertEqual(P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM[-1], 1000)

        for kwargs in (
            {"steadyshot_movie": "STANDARD"},
            {"e_mount_sony_lens": False},
            {"shoot_mode": "S_AND_Q"},
            {"frame_rate_fps": 119.88},
            {"external_hdmi_recorder_active": True},
        ):
            gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                expect_catalyst_gyro_available=True, **kwargs
            )
            self.assertFalse(gc.passed)
            self._assert_err(gc, P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST)

        self.assertFalse(
            evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                claimed_200mm_active_still_documented_in_ver7=True
            ).passed
        )
        for dorm in P368_DORMANT_STEADYSHOT_MODES:
            self.assertFalse(
                evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                    dormant_steadyshot_mode_requested=dorm
                ).passed
            )

    def test_034_wave78_2_fx6_zero_body_ibis_and_3step_lens_oss(self) -> None:
        self.assertEqual(P368_FX6_BODY_IBIS_COUNT, 0)
        self.assertEqual(P368_FX6_IBIS_UNSUPPORTED_SYMBOL, "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED")
        self.assertEqual(P368_FX6_LENS_OSS_MODES, ("ACTIVE", "STANDARD", "OFF"))

        for oss in P368_FX6_LENS_OSS_MODES:
            self.assertTrue(
                evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
                    fx6_lens_oss_mode=oss
                ).passed
            )

        for kwargs in (
            {"claimed_fx6_has_body_ibis": True},
            {"claimed_fx6_lens_oss_only_on_off": True},
            {"fx6_lens_oss_mode": "ACTIVE", "expect_fx6_catalyst_ok_with_oss_on": True},
        ):
            gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(**kwargs)
            self.assertFalse(gc.passed)
            self._assert_err(gc, P368_GC_ERR_FX6_ZERO_IBIS_OR_3STEP_LENS_OSS)

    # ------------------------------------------------------------------
    # 8. Wave 78.3 (Group D): Photo Capture, G126 View Mode 3, Rating & Slot 1
    # ------------------------------------------------------------------

    def test_035_wave78_3_photo_capture_mp_dci4k_block_and_pb_heif_reset_immunity(self) -> None:
        gd_4k = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            source_file_format="XAVC_S_4K", source_resolution_4k=True, photo_capture_requested=True
        )
        self.assertTrue(gd_4k.passed)
        self.assertEqual(gd_4k.photo_capture_output_mp, P368_PHOTO_CAPTURE_4K_MP)

        gd_hd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            source_file_format="XAVC_S_HD", source_resolution_4k=False, photo_capture_requested=True
        )
        self.assertTrue(gd_hd.passed)
        self.assertEqual(gd_hd.photo_capture_output_mp, P368_PHOTO_CAPTURE_HD_MP)

        gd_dci = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            source_file_format="XAVC_S_I_DCI_4K", photo_capture_requested=True
        )
        self.assertFalse(gd_dci.passed)
        self.assertTrue(gd_dci.photo_capture_dci4k_blocked)
        self.assertIsNone(gd_dci.photo_capture_output_mp)
        self._assert_err(gd_dci, P368_GD_ERR_PHOTO_CAPTURE_DCI4K_OR_HEIF_RESET)

        gd_heif_rst = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            pb_jpeg_heif_switch="HEIF_422", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gd_heif_rst.passed)
        self.assertEqual(gd_heif_rst.effective_pb_jpeg_heif_after_reset, "HEIF_422")
        self.assertTrue(gd_heif_rst.pb_jpeg_heif_resists_camera_reset)

        gd_heif_init = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            pb_jpeg_heif_switch="HEIF_422", reset_action="INITIALIZE"
        )
        self.assertTrue(gd_heif_init.passed)
        self.assertEqual(gd_heif_init.effective_pb_jpeg_heif_after_reset, "JPEG")

    def test_036_wave78_3_g126_view_mode_exact_3_items_rating_and_slot1_erofs30(self) -> None:
        self.assertEqual(P368_VIEW_MODE_EXACT_3_ITEMS, ("DATE_VIEW", "FOLDER_VIEW_STILL", "MOVIE_VIEW"))
        self.assertEqual(P368_VIEW_MODE_DORMANT_ITEMS, ("FOLDER_VIEW_MP4", "AVCHD_VIEW", "XAVC_S_VIEW"))
        self.assertEqual(P368_FX6_PHOTO_CAPTURE_UI_COUNT, 0)
        self.assertEqual(P368_FX6_CLIP_FLAGS, ("OK", "NG", "KEEP"))

        for vm in P368_VIEW_MODE_EXACT_3_ITEMS:
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                view_mode=vm, reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(gd.passed)
            self.assertEqual(gd.effective_view_mode_after_reset, vm)

        for dorm in P368_VIEW_MODE_DORMANT_ITEMS:
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                dormant_view_mode_requested=dorm
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30)

        gd_slot1_photo = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            photo_capture_requested=True, photo_capture_target_slot=1
        )
        self.assertFalse(gd_slot1_photo.passed)
        self._assert_err(gd_slot1_photo, P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30)

        gd_slot1_rate = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            rating_stars=5, rating_write_requested=True, rating_write_target_slot=1
        )
        self.assertFalse(gd_slot1_rate.passed)
        self._assert_err(gd_slot1_rate, P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30)

        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                claimed_fx6_has_photo_capture=True
            ).passed
        )

    # ------------------------------------------------------------------
    # 9. Wave 78.4 (Group D): No-UVC Disproof, SRT Caller, 38 Mbps & Airplane Mode
    # ------------------------------------------------------------------

    def test_037_wave78_4_zero_native_uvc_usb_streaming_and_4k_30p_rumor_disproof(self) -> None:
        self.assertFalse(P368_FX3_UVC_STREAMING_SUPPORTED)
        self.assertEqual(len(P368_USB_CONNECTION_EXACT_4_MODES), 4)
        self.assertIn("4K_15P", P368_FX3_DORMANT_UVC_FORMATS)
        self.assertNotIn("4K_30P", P368_FX3_DORMANT_UVC_FORMATS)

        for kwargs in (
            {"dormant_uvc_usb_streaming_requested": True},
            {"claimed_fx3_supports_uvc_4k_30p": True},
            {"claimed_movie_rec_during_streaming_is_uvc": True},
            {"usb_connection_modes_exposed": P368_USB_CONNECTION_EXACT_4_MODES + ("USB_STREAMING",)},
        ):
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(**kwargs)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P368_GD_ERR_NO_UVC_USB_STREAMING_DISPROOF)

    def test_038_wave78_4_outbound_srt_caller_and_url_syntax_firewall(self) -> None:
        self.assertEqual(P368_SRT_EXPOSED_ROLES, ("SRT_CALLER",))
        gd_ok = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            streaming_active=True,
            streaming_protocol="SRT",
            srt_role="SRT_CALLER",
            srt_url_syntax="srt.example.invalid",
            streaming_codec="H265",
            streaming_encryption="AES_256",
            streaming_transport="USB_LAN",
            airplane_mode="ON",
        )
        self.assertTrue(gd_ok.passed)
        self.assertFalse(gd_ok.srt_listener_supported)
        self.assertTrue(gd_ok.usb_lan_bypasses_airplane_mode)

        for kwargs in (
            {"srt_role": "SRT_LISTENER"},
            {"claimed_fx3_supports_srt_listener": True},
            {"srt_url_syntax": "srt.example.invalid:9000"},
            {"srt_url_syntax": "srt.example.invalid?streamid=live"},
            {"streaming_protocol": "RTMP", "streaming_codec": "H265"},
            {"streaming_protocol": "RTMPS", "streaming_codec": "H265"},
            {"streaming_active": True, "creators_app_bt_configured": False},
        ):
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(**kwargs)
            self.assertFalse(gd.passed)
            self._assert_err(gd, P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF)

    def test_039_wave78_4_38mbps_fps_ceiling_and_airplane_mode_zero_rf(self) -> None:
        self.assertEqual(P368_STREAMING_MAX_BITRATE_MBPS, 38.0)
        self.assertEqual(len(P368_STREAMING_PROFILES), 8)
        self.assertEqual(P368_FX6_NATIVE_UVC_COUNT, 0)
        self.assertEqual(P368_FX6_BUILTIN_STREAMING_COUNT, 0)
        self.assertEqual(P368_FX6_EXTERNAL_STREAMING_ADAPTERS, ("CBK-WA100", "CBK-RPU7", "PDT-FP1"))

        for bad_fps in P368_STREAMING_BLOCKED_FPS:
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                streaming_fps=bad_fps
            )
            self.assertFalse(gd.passed)
            self._assert_err(gd, P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF)

        for ok_fps in P368_STREAMING_ALLOWED_FPS:
            self.assertTrue(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                    streaming_fps=ok_fps
                ).passed
            )

        gd_over = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            streaming_profile="4K_2160P_60P_50P", streaming_bitrate_mbps=45.0
        )
        self.assertFalse(gd_over.passed)
        self._assert_err(gd_over, P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF)

        gd_wifi_air = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            streaming_active=True, streaming_transport="WIFI", airplane_mode="ON"
        )
        self.assertFalse(gd_wifi_air.passed)

        gd_net_rst = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            airplane_mode="ON", reset_action="RESET_NETWORK_SET"
        )
        self.assertTrue(gd_net_rst.passed)
        self.assertEqual(gd_net_rst.effective_airplane_mode_after_reset, "ON")

        gd_init = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            airplane_mode="ON", reset_action="INITIALIZE"
        )
        self.assertTrue(gd_init.passed)
        self.assertEqual(gd_init.effective_airplane_mode_after_reset, "OFF")

        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                claimed_fx6_has_native_uvc_or_builtin_srt_rtmp=True
            ).passed
        )

    # ------------------------------------------------------------------
    # 10. Tier-0 Receipts, 16/16 H0 == H3, Redlines, Verifier & Markdown
    # ------------------------------------------------------------------

    def test_040_tier0_offline_default_blocks_without_receipts_and_dry_run_passes(self) -> None:
        rep_off = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=False
        )
        self.assertEqual(
            rep_off.overall_status, P368_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        )
        self.assertEqual(rep_off.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(rep_off.tier0_receipt_verified)
        self.assertEqual(rep_off.h0_equals_h3_count, 0)
        self.assertFalse(rep_off.ready_for_live_camera_attach)
        self.assertTrue(verify_phase368_report(rep_off).valid)

        rep_dry = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep_dry.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep_dry.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep_dry.tier0_receipt_verified)
        self.assertEqual(rep_dry.h0_equals_h3_count, 16)
        self.assertFalse(rep_dry.ready_for_live_camera_attach)
        self.assertTrue(verify_phase368_report(rep_dry).valid)

    def test_041_tier0_physical_dual_media_receipts_verified_from_files_distinct_st_dev(self) -> None:
        sim = build_simulated_phase368_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "FX3RCPT1_A.bin"
            pb = Path(td) / "FX3RCPT1_B.bin"
            pa.write_bytes(sim["receipt_a_bytes"])
            pb.write_bytes(sim["receipt_b_bytes"])
            rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
                force_clean_room=True,
                receipt_a_path=pa,
                receipt_b_path=pb,
                st_dev_a_override=2101,
                st_dev_b_override=2102,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=sim["h0_baselines_b"],
                h3_baselines=sim["h3_baselines"],
            )
            self.assertEqual(
                rep.go_no_go,
                P368_GO_NO_GO_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_VERIFIED,
            )
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertFalse(rep.ready_for_live_camera_attach)
            self.assertTrue(verify_phase368_report(rep).valid)

    def test_042_tier0_rejects_same_st_dev_trivial_serial_cid_and_h0_h3_drift(self) -> None:
        sim = build_simulated_phase368_tier0_receipts()
        base = {
            "force_clean_room": True,
            "receipt_a_bytes": sim["receipt_a_bytes"],
            "receipt_b_bytes": sim["receipt_b_bytes"],
            "st_dev_a_override": 5001,
            "st_dev_b_override": 5002,
            "body_serial": sim["body_serial"],
            "emmc_cid": sim["emmc_cid"],
            "h0_baselines_a": sim["h0_baselines_a"],
            "h0_baselines_b": sim["h0_baselines_b"],
            "h3_baselines": sim["h3_baselines"],
        }

        rep_same = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            **{**base, "st_dev_b_override": 5001}
        )
        self.assertFalse(rep_same.tier0_receipt_verified)
        self._assert_err(rep_same, P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        rep_serial = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            **{**base, "body_serial": "00000000000000"}
        )
        self.assertFalse(rep_serial.tier0_receipt_verified)

        rep_cid = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            **{**base, "emmc_cid": "0" * 32}
        )
        self.assertFalse(rep_cid.tier0_receipt_verified)

        bad_h3 = dict(sim["h3_baselines"])
        bad_h3[REQUIRED_H0_BASELINE_KEYS[0]] = "f" * 64
        rep_drift = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            **{**base, "h3_baselines": bad_h3}
        )
        self.assertFalse(rep_drift.tier0_receipt_verified)
        self._assert_err(rep_drift, P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_043_redline_telemetry_and_auth_claims_fail_closed(self) -> None:
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
            rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
                force_clean_room=True, simulate_bench_dry_run=True, **kw
            )
            self.assertEqual(
                rep.go_no_go,
                P368_GO_NO_GO_BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE,
            )
            self.assertFalse(rep.ready_for_live_camera_attach)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertEqual(rep.emmc_write_count, 0)
            self.assertEqual(rep.rf_packets_transmitted, 0)
            self._assert_err(rep, P368_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION)

    def test_044_verify_phase368_report_detects_tampering(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["ready_for_live_camera_attach"] = True
        res = verify_phase368_report(d)
        self.assertFalse(res.valid)
        self.assertTrue(any("ready_for_live_camera_attach" in e for e in res.errors))

        d2 = copy.deepcopy(rep.to_dict())
        d2["emmc_write_count"] = 1
        res2 = verify_phase368_report(d2)
        self.assertFalse(res2.valid)
        self.assertTrue(any("emmc_write_count" in e for e in res2.errors))

    def test_045_additional_wave_77_78_boundary_assertions(self) -> None:
        # 46: Invalid media_card_speed rejected
        ga_card = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            media_card_speed="SD_CLASS2"
        )
        self.assertFalse(ga_card.passed)
        self._assert_err(ga_card, P368_GA_ERR_CARD_SPEED_V60_V90_VPG200_VPG400)

    def test_046_wave77_1_all_6_media_card_speed_tiers_valid(self) -> None:
        for spd in P368_VALID_MEDIA_CARD_SPEEDS:
            self.assertTrue(
                evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                    file_format="XAVC_S_HD",
                    record_setting_mbps=50,
                    media_card_speed=spd,
                ).passed
            )

    def test_047_wave77_1_xavc_s_i_4k_sq_120fps_without_proxy_requires_vpg200(self) -> None:
        ga_v90 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_4K",
            sq_frame_rate_fps=120,
            record_setting_mbps=1200,
            proxy_recording_enabled=False,
            media_card_speed="SDXC_V90",
        )
        self.assertFalse(ga_v90.passed)
        self.assertEqual(ga_v90.required_min_card_speed, "CFEA_VPG200")
        self.assertFalse(ga_v90.vpg400_proxy_threshold_triggered)

        ga_vpg200 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_4K",
            sq_frame_rate_fps=120,
            record_setting_mbps=1200,
            proxy_recording_enabled=False,
            media_card_speed="CFEA_VPG200",
        )
        self.assertTrue(ga_vpg200.passed)

    def test_048_wave77_1_xavc_s_i_hd_sq_240fps_requires_vpg200_and_proxy_vpg400(self) -> None:
        ga_no_proxy = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_HD",
            sq_frame_rate_fps=240,
            record_setting_mbps=890,
            proxy_recording_enabled=False,
            media_card_speed="CFEA_VPG200",
        )
        self.assertTrue(ga_no_proxy.passed)
        self.assertEqual(ga_no_proxy.required_min_card_speed, "CFEA_VPG200")

        ga_proxy = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_S_I_HD",
            sq_frame_rate_fps=240,
            record_setting_mbps=890,
            proxy_recording_enabled=True,
            media_card_speed="CFEA_VPG200",
        )
        self.assertFalse(ga_proxy.passed)
        self.assertTrue(ga_proxy.vpg400_proxy_threshold_triggered)
        self.assertEqual(ga_proxy.required_min_card_speed, "CFEA_VPG400")

    def test_049_wave77_1_xavc_hs_4k_sq_120fps_requires_v90(self) -> None:
        ga_v60 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="S_AND_Q",
            file_format="XAVC_HS_4K",
            sq_frame_rate_fps=120,
            media_card_speed="SDXC_V60",
        )
        self.assertFalse(ga_v60.passed)
        self.assertEqual(ga_v60.required_min_card_speed, "SDXC_V90")

    def test_050_wave77_1_movie_280mbps_requires_v60(self) -> None:
        ga_v30 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            shoot_mode="MOVIE",
            file_format="XAVC_HS_4K",
            rec_frame_rate_fps=119.88,
            prev_rec_frame_rate_fps=119.88,
            record_setting_mbps=280,
            media_card_speed="SDXC_U3_V30",
        )
        self.assertFalse(ga_v30.passed)
        self.assertEqual(ga_v30.required_min_card_speed, "SDXC_V60")

    def test_051_wave77_1_movie_100mbps_requires_v30_and_50mbps_class10(self) -> None:
        ga_v30 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_4K", record_setting_mbps=100, media_card_speed="SDHC_CLASS10"
        )
        self.assertFalse(ga_v30.passed)
        self.assertEqual(ga_v30.required_min_card_speed, "SDXC_U3_V30")

        ga_c10 = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            file_format="XAVC_S_HD", record_setting_mbps=50, media_card_speed="SDHC_CLASS10"
        )
        self.assertTrue(ga_c10.passed)
        self.assertEqual(ga_c10.required_min_card_speed, "SDHC_CLASS10")

    def test_052_wave77_1_model_id_and_fw_floor_enforced(self) -> None:
        ga_model = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            body_model_id=0x91030079
        )
        self.assertFalse(ga_model.passed)
        self._assert_err(ga_model, P368_GA_ERR_MODEL_OR_FW_FLOOR)

        ga_fw = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(body_fw="6.01")
        self.assertFalse(ga_fw.passed)
        self._assert_err(ga_fw, P368_GA_ERR_MODEL_OR_FW_FLOOR)

        ga_hg = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            sony_help_guide_id="ilc/9999"
        )
        self.assertFalse(ga_hg.passed)
        self._assert_err(ga_hg, P368_GA_ERR_MODEL_OR_FW_FLOOR)

    def test_053_wave77_2_flexible_iso_keeps_awb_priority_effective(self) -> None:
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            log_shooting_mode="FLEXIBLE_ISO", awb_priority_set="AMBIENCE"
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.awb_priority_effective_in_log)

    def test_054_wave77_2_movie_awb_lock_custom_keys_validated(self) -> None:
        for k in ("NONE", "AWB_LOCK_HOLD", "AWB_LOCK_TOGGLE"):
            self.assertTrue(
                evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                    movie_awb_lock_custom_key=k
                ).passed
            )
        self.assertFalse(
            evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                movie_awb_lock_custom_key="SHUTTER_HALF_PRESS"
            ).passed
        )

    def test_055_wave77_2_claimed_awb_priority_resists_camera_reset_rejected(self) -> None:
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            claimed_awb_priority_resists_camera_reset=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P368_GA_ERR_AWB_PRIORITY_SHUTTER_LOCK_OR_KELVIN)

    def test_056_wave77_2_fx6_kelvin_bounds_and_shockless_white(self) -> None:
        for k in (1999, 15001):
            ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(fx6_kelvin_temp_k=k)
            self.assertFalse(ga.passed)
            self._assert_err(ga, P368_GA_ERR_FX6_ATW_OR_WHT_BAL)
        for sw in ("OFF", "1", "2", "3"):
            self.assertTrue(
                evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
                    fx6_shockless_white=sw
                ).passed
            )

    def test_057_wave77_1_claimed_fx6_xavc_l_dci4k_rejected(self) -> None:
        ga = evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(
            claimed_fx6_xavc_l_supports_dci4k=True
        )
        self.assertFalse(ga.passed)
        self._assert_err(ga, P368_GA_ERR_FX6_REC_FORMAT_OR_CLASS300)

    def test_058_wave77_3_initial_focus_mag_still_vs_movie_constraints(self) -> None:
        self.assertTrue(
            evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                shoot_mode="PHOTO", initial_focus_mag="X1_5"
            ).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                shoot_mode="MOVIE", initial_focus_mag="X2_1"
            ).passed
        )
        self.assertTrue(
            evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                shoot_mode="MOVIE", initial_focus_mag="X4_0"
            ).passed
        )

    def test_059_wave77_3_peaking_levels_and_colors_validated(self) -> None:
        for lvl in ("HIGH", "MID", "LOW"):
            for col in ("RED", "YELLOW", "BLUE", "WHITE"):
                self.assertTrue(
                    evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                        peaking_display="ON", peaking_level=lvl, peaking_color=col
                    ).passed
                )
        self.assertFalse(
            evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                peaking_color="GREEN"
            ).passed
        )

    def test_060_wave77_3_touch_operation_modes_and_swipe_up_validated(self) -> None:
        for op in ("ON", "ON_PLAYBACK_ONLY", "OFF"):
            for sens in ("STANDARD", "SENSITIVE"):
                for fn in ("TOUCH_TRACKING", "TOUCH_FOCUS", "OFF"):
                    self.assertTrue(
                        evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
                            touch_operation=op,
                            touch_sensitivity=sens,
                            touch_func_in_shooting=fn,
                        ).passed
                    )

    def test_061_wave77_4_airplane_mode_off_does_not_silence_update_red_dot(self) -> None:
        gb = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            airplane_mode="OFF"
        )
        self.assertTrue(gb.passed)
        self.assertFalse(gb.version_update_red_dot_silenced)

    def test_062_wave77_3_invalid_focus_assistant_or_peaking_item_list_rejected(self) -> None:
        gb_fa = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            focus_assistant_items=("Auto Magnifier in MF", "Focus Magnif. Time")
        )
        self.assertFalse(gb_fa.passed)
        self._assert_err(gb_fa, P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET)

        gb_pk = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            peaking_items=("Peaking Display", "Peaking Level")
        )
        self.assertFalse(gb_pk.passed)
        self._assert_err(gb_pk, P368_GB_ERR_FOCUS_ASSIST_OR_PEAKING_G109_RESET)

    def test_063_wave77_3_invalid_touch_operation_items_or_fx6_peaking_items_rejected(self) -> None:
        gb_to = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            touch_operation_items=("Touch Operation",)
        )
        self.assertFalse(gb_to.passed)
        self._assert_err(gb_to, P368_GB_ERR_TOUCH_OPERATION_OR_DORMANT_TOUCHPAD)

        gb_fx6 = evaluate_p368_check_group_b_focusassist_peaking_touch_screenreader_version(
            fx6_peaking_items=("Setting", "Peaking Level", "Color", "Frequency")
        )
        self.assertFalse(gb_fx6.passed)
        self._assert_err(gb_fx6, P368_GB_ERR_FX6_PEAKING_DORMANT_FREQ_OR_MAG)

    def test_064_wave78_1_shutter_mode_resets_to_speed_under_camera_reset(self) -> None:
        gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            shutter_mode="ANGLE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.effective_shutter_mode_after_reset, "SPEED")

    def test_065_wave78_1_invalid_auto_manual_switches_or_angle_rejected(self) -> None:
        for kw in (
            {"exposure_ctrl_type": "CINE_EI"},
            {"av_auto_manual_switch": "LOCKED"},
            {"tv_auto_manual_switch": "LOCKED"},
            {"iso_auto_manual_switch": "LOCKED"},
            {"auto_slow_shutter": "AUTO"},
            {"shutter_mode": "ECS"},
            {"shutter_angle_value": "179.9"},
        ):
            self.assertFalse(
                evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(**kw).passed
            )

    def test_066_wave78_2_steadyshot_resets_to_standard_under_camera_reset(self) -> None:
        gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            steadyshot_movie="ACTIVE", reset_action="CAMERA_SETTINGS_RESET"
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.effective_steadyshot_movie, "STANDARD")

    def test_067_wave78_2_invalid_focal_table_or_focal_length_rejected(self) -> None:
        gc_len = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            exposed_focal_lengths_mm=P368_IBIS_EXACT_47_FOCAL_LENGTHS_MM[:-1]
        )
        self.assertFalse(gc_len.passed)
        self._assert_err(gc_len, P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST)

        gc_mm = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            steadyshot_adjust="MANUAL", steadyshot_focal_length_mm=33
        )
        self.assertFalse(gc_mm.passed)
        self._assert_err(gc_mm, P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST)

    def test_068_wave78_2_claimed_steadyshot_resists_camera_reset_rejected(self) -> None:
        gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            claimed_steadyshot_resists_camera_reset=True
        )
        self.assertFalse(gc.passed)
        self._assert_err(gc, P368_GC_ERR_STEADYSHOT_ACTIVE_LOCKOUT_OR_CATALYST)

    def test_069_wave78_2_steadyshot_off_with_e_mount_allows_catalyst_rtmd(self) -> None:
        gc = evaluate_p368_check_group_c_flexexp_shutterangle_activeibis_catalyst(
            steadyshot_movie="OFF",
            e_mount_sony_lens=True,
            shoot_mode="MOVIE",
            frame_rate_fps=23.98,
            external_hdmi_recorder_active=False,
        )
        self.assertTrue(gc.passed)
        self.assertTrue(gc.catalyst_gyro_rtmd_available)

    def test_070_wave78_3_pb_jpeg_heif_all_3_modes_and_rating_0_to_5(self) -> None:
        for fmt in P368_PB_JPEG_HEIF_MODES:
            for stars in range(0, 6):
                self.assertTrue(
                    evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                        pb_jpeg_heif_switch=fmt, rating_stars=stars
                    ).passed
                )
        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                rating_stars=6
            ).passed
        )
        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                rating_stars=-1
            ).passed
        )

    def test_071_wave78_3_reset_resistance_claims_rejected(self) -> None:
        for kw in (
            {"claimed_pb_jpeg_heif_wiped_by_camera_reset": True},
            {"claimed_view_mode_wiped_by_camera_reset": True},
            {"claimed_rating_wiped_by_camera_reset": True},
        ):
            self.assertFalse(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(**kw).passed
            )

    def test_072_wave78_3_view_mode_initialize_resets_to_date_view(self) -> None:
        gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            view_mode="MOVIE_VIEW", reset_action="INITIALIZE"
        )
        self.assertTrue(gd.passed)
        self.assertEqual(gd.effective_view_mode_after_reset, "DATE_VIEW")

    def test_073_wave78_3_fx6_clip_flags_ok_ng_keep_and_invalid_rejected(self) -> None:
        for fl in P368_FX6_CLIP_FLAGS:
            self.assertTrue(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                    fx6_clip_flag=fl
                ).passed
            )
        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                fx6_clip_flag="STAR_5"
            ).passed
        )

    def test_074_wave78_4_movie_rec_during_streaming_constraints(self) -> None:
        # 4K_2160P_30P_25P forbids concurrent 4K Movie Rec During Streaming
        gd_4k_bad = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            streaming_profile="4K_2160P_30P_25P",
            streaming_bitrate_mbps=34.0,
            movie_rec_during_streaming="ENABLE",
            movie_rec_during_streaming_4k_requested=True,
            movie_rec_during_streaming_slot=2,
        )
        self.assertFalse(gd_4k_bad.passed)
        self._assert_err(gd_4k_bad, P368_GD_ERR_SRT_CALLER_BITRATE_FPS_OR_AIRPLANE_RF)

        # S&Q forbids Movie Rec During Streaming=ENABLE
        gd_sq_bad = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            shoot_mode="S_AND_Q",
            movie_rec_during_streaming="ENABLE",
            movie_rec_during_streaming_slot=2,
        )
        self.assertFalse(gd_sq_bad.passed)

        # Slot 1 blocked EROFS=30
        gd_slot1_bad = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            movie_rec_during_streaming="ENABLE",
            movie_rec_during_streaming_slot=1,
        )
        self.assertFalse(gd_slot1_bad.passed)
        self._assert_err(gd_slot1_bad, P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30)

        # HD_1080P_60P_50P allows concurrent Movie Rec on Slot 2
        gd_ok = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            streaming_profile="HD_1080P_60P_50P",
            streaming_bitrate_mbps=9.0,
            movie_rec_during_streaming="ENABLE",
            movie_rec_during_streaming_4k_requested=True,
            movie_rec_during_streaming_slot=2,
        )
        self.assertTrue(gd_ok.passed)

    def test_075_wave78_4_all_8_streaming_profiles_at_max_bitrate_accepted(self) -> None:
        for prof, (_b_min, b_max, _b_def, _allow4k) in P368_STREAMING_PROFILES.items():
            gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                streaming_profile=prof, streaming_bitrate_mbps=b_max
            )
            self.assertTrue(gd.passed, msg=f"Profile {prof} failed at {b_max}: {gd.errors}")

    def test_076_wave78_4_airplane_mode_usb_lan_claims_rejected(self) -> None:
        for kw in (
            {"expect_airplane_mode_blocks_usb_lan": True},
            {"claimed_reset_network_set_wipes_airplane_mode": True},
            {"claimed_initialize_preserves_airplane_mode": True},
            {"claimed_streaming_wiped_by_camera_reset": True},
            {"airplane_mode": "OFF"},
        ):
            self.assertFalse(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(**kw).passed
            )

    def test_077_tier0_missing_single_receipt_or_wrong_size_rejected(self) -> None:
        sim = build_simulated_phase368_tier0_receipts()
        rep_one = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, receipt_a_bytes=sim["receipt_a_bytes"]
        )
        self.assertFalse(rep_one.tier0_receipt_verified)
        self._assert_err(rep_one, P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

        rep_sz = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True,
            receipt_a_bytes=b"SHORT",
            receipt_b_bytes=b"SHORT",
            st_dev_a_override=11,
            st_dev_b_override=12,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(rep_sz.tier0_receipt_verified)
        self._assert_err(rep_sz, P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_078_tier0_divergent_h0_copy_a_vs_copy_b_rejected(self) -> None:
        sim = build_simulated_phase368_tier0_receipts()
        bad_h0_b = dict(sim["h0_baselines_b"])
        bad_h0_b[REQUIRED_H0_BASELINE_KEYS[1]] = "a" * 64
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True,
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=2201,
            st_dev_b_override=2202,
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=bad_h0_b,
            h3_baselines=sim["h3_baselines"],
        )
        self.assertFalse(rep.tier0_receipt_verified)
        self._assert_err(rep, P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_079_tier0_simulated_h0_h3_drift_reduces_parity_count(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            simulated_h0_h3_drifted_surfaces=2,
        )
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 14)
        self._assert_err(rep, P368_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)

    def test_080_tier0_missing_file_paths_rejected(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True,
            receipt_a_path=Path("/nonexistent/phase368_a.bin"),
            receipt_b_path=Path("/nonexistent/phase368_b.bin"),
        )
        self.assertFalse(rep.tier0_receipt_verified)
        self._assert_err(rep, P368_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)

    def test_081_deterministic_json_has_no_timing_keys(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        raw = rep.to_deterministic_json()
        parsed = json.loads(raw)
        self.assertNotIn("elapsed_seconds", parsed["donor_inspection"])
        self.assertEqual(parsed["report_sha256"], rep.report_sha256)

    def test_082_markdown_renders_headers_warnings_and_errors(self) -> None:
        rep_off = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True
        )
        md_off = render_phase368_markdown(rep_off)
        self.assertIn("Phase 368", md_off)
        self.assertIn("## Warnings", md_off)
        self.assertIn("ready_for_live_camera_attach=False", md_off)

        rep_fail = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True, fx3_screen_reader_requested=True
        )
        md_fail = render_phase368_markdown(rep_fail)
        self.assertIn("## Errors", md_fail)

    def test_083_check_group_ids_exact_and_report_flags_locked(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep.check_group_a.group_id, P368_CHECK_GROUP_A_ID)
        self.assertEqual(rep.check_group_b.group_id, P368_CHECK_GROUP_B_ID)
        self.assertEqual(rep.check_group_c.group_id, P368_CHECK_GROUP_C_ID)
        self.assertEqual(rep.check_group_d.group_id, P368_CHECK_GROUP_D_ID)
        self.assertFalse(rep.fx3_screen_reader_exposed)
        self.assertFalse(rep.fx6_screen_reader_exposed)
        self.assertFalse(rep.fx3_touch_panel_pad_exposed)
        self.assertFalse(rep.fx3_var_shutter_exposed)
        self.assertFalse(rep.fx6_body_ibis_present)
        self.assertFalse(rep.fx3_uvc_streaming_supported)
        self.assertFalse(rep.fx3_srt_listener_supported)
        self.assertTrue(rep.fx3_view_mode_3items_exact)

    def test_084_mode_equivalence_parity_across_clean_room_mechanisms(self) -> None:
        r_flag = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            r_env1 = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env2 = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
                simulate_bench_dry_run=True
            )
        with mock.patch(f"{VERIFIER_MOD}._resolve_work_root_or_none", return_value=None):
            r_mock = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
                force_clean_room=False, simulate_bench_dry_run=True
            )
        r_none = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=False,
            work_root=Path("/nonexistent/phase368_parity"),
            simulate_bench_dry_run=True,
        )
        self.assertEqual(r_flag.report_sha256, r_env1.report_sha256)
        self.assertEqual(r_flag.report_sha256, r_env2.report_sha256)
        self.assertEqual(r_flag.report_sha256, r_mock.report_sha256)
        self.assertEqual(r_flag.report_sha256, r_none.report_sha256)

    def test_085_verify_report_rejects_bad_schema_go_no_go_and_sha(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["schema_version"] = "wrong_schema"
        d["go_no_go"] = "INVALID_STATUS"
        d["report_sha256"] = "0" * 64
        res = verify_phase368_report(d)
        self.assertFalse(res.valid)
        self.assertGreaterEqual(len(res.errors), 3)

    def test_086_verify_report_rejects_verified_claim_without_tier0_or_4_groups(self) -> None:
        rep = run_movieset_vpg_awbprio_screenreader_flexexp_shutterangle_photocap_and_srt_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        d = copy.deepcopy(rep.to_dict())
        d["tier0_receipt_verified"] = False
        d["check_groups_passed"] = 3
        res = verify_phase368_report(d)
        self.assertFalse(res.valid)

    def test_087_group_d_slot1_write_requested_rejected_erofs30(self) -> None:
        gd = evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
            slot1_write_requested=True
        )
        self.assertFalse(gd.passed)
        self._assert_err(gd, P368_GD_ERR_VIEW_MODE_3ITEM_OR_RATING_SLOT1_EROFS30)
        self.assertEqual(gd.slot1_data_sector_writes, 0)
        self.assertFalse(gd.slot1_tier0_vault_mutated)

    def test_088_group_d_srt_protocols_and_encryption_matrix(self) -> None:
        for enc in ("NONE", "AES_128", "AES_256"):
            for codec in ("H264", "H265"):
                self.assertTrue(
                    evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                        streaming_protocol="SRT",
                        streaming_codec=codec,
                        streaming_encryption=enc,
                    ).passed
                )
        for proto in ("RTMP", "RTMPS"):
            self.assertTrue(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                    streaming_protocol=proto, streaming_codec="H264"
                ).passed
            )

    def test_089_group_d_usb_connection_modes_all_4_valid(self) -> None:
        for mode in P368_USB_CONNECTION_EXACT_4_MODES:
            self.assertTrue(
                evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                    usb_connection_mode=mode
                ).passed
            )
        self.assertFalse(
            evaluate_p368_check_group_d_photocap_viewmode_rating_uvc_srt_and_tier0(
                usb_connection_mode="USB_STREAMING"
            ).passed
        )

    def test_090_group_a_record_setting_invalid_shoot_or_log_or_reset_rejected(self) -> None:
        for kw in (
            {"shoot_mode": "TIMELAPSE"},
            {"log_shooting_mode": "SLOG2"},
            {"reset_action": "FACTORY_WIPE"},
        ):
            self.assertFalse(
                evaluate_p368_check_group_a_movieset_vpg_awbprio_and_fx6_atw(**kw).passed
            )

    # ------------------------------------------------------------------
    # 11. CLI Subprocess Tests (Long Command + Short Alias `preflight-phase368`, All 4 Modes)
    # ------------------------------------------------------------------

    def test_091_cli_help_long_and_alias_succeed_with_percent_escaping(self) -> None:
        for cmd in (CLI_CMD_LONG, CLI_CMD_ALIAS):
            cp = self._run_cli([cmd, "--help"])
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertIn("preflight", cp.stdout.lower())

    def test_092_cli_offline_default_returns_rc2_both_long_and_alias(self) -> None:
        cp_long = self._run_cli([CLI_CMD_LONG, "--json"], clear_clean_room_env=True)
        cp_alias = self._run_cli([CLI_CMD_ALIAS, "--json"], clear_clean_room_env=True)
        self.assertEqual(cp_long.returncode, 2, msg=cp_long.stderr)
        self.assertEqual(cp_alias.returncode, 2, msg=cp_alias.stderr)
        d1 = json.loads(cp_long.stdout)
        d2 = json.loads(cp_alias.stdout)
        self.assertEqual(d1["report_sha256"], d2["report_sha256"])
        self.assertEqual(d1["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(d1["ready_for_live_camera_attach"])

    def test_093_cli_dry_run_returns_rc0_normal_mode(self) -> None:
        cp = self._run_cli([CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"], clear_clean_room_env=True)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertFalse(data["ready_for_live_camera_attach"])
        self.assertTrue(verify_phase368_report(data).valid)

    def test_094_cli_dry_run_fx3_clean_room_test_env_mode(self) -> None:
        cp = self._run_cli(
            [CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_CLEAN_ROOM_TEST": "1"},
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)

    def test_095_cli_dry_run_force_clean_room_env_mode(self) -> None:
        cp = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)

    def test_096_cli_dry_run_force_clean_room_flag_donorless_mode(self) -> None:
        cp = self._run_cli(
            [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json"],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["donor_inspection"]["bytes_read_total"], 0)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_097_cli_summary_flag_formats_single_line_digest(self) -> None:
        cp = self._run_cli(
            [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--summary"],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", cp.stdout)
        self.assertIn("h0_eq_h3=16/16", cp.stdout)
        self.assertIn("ready_attach=False", cp.stdout)

    def test_098_cli_markdown_out_and_output_json_files_written(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            md_path = Path(td) / "p368.md"
            json_path = Path(td) / "p368.json"
            cp = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--markdown-out",
                    str(md_path),
                    "--output",
                    str(json_path),
                    "--summary",
                ],
                clear_clean_room_env=True,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("Phase 368", md_path.read_text(encoding="utf-8"))
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase368_report(loaded).valid)

    def test_099_cli_failure_flags_return_rc2_blocked(self) -> None:
        for flag in (
            ["--fx3-screen-reader-requested"],
            ["--dormant-uvc-usb-streaming-requested"],
            ["--bodydata-slot1-flash-requested"],
            ["--claimed-fx6-has-body-ibis"],
            ["--dormant-var-shutter-requested"],
            ["--slot1-write-requested"],
        ):
            cp = self._run_cli(
                [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", *flag, "--summary"],
                clear_clean_room_env=True,
            )
            self.assertEqual(cp.returncode, 2, msg=f"Expected rc=2 for {flag}: {cp.stdout}")
            self.assertIn("BLOCKED_MOVIESET_VPG_AWBPRIO_SCREENREADER_FLEXEXP_SHUTTERANGLE_PHOTOCAP_AND_SRT_FAILURE", cp.stdout)

    def test_100_cli_all_4_modes_identical_clean_room_hash(self) -> None:
        cp1 = self._run_cli(
            [CLI_CMD_ALIAS, "--force-clean-room", "--simulate-bench-dry-run", "--json"],
            clear_clean_room_env=True,
        )
        cp2 = self._run_cli(
            [CLI_CMD_LONG, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_CLEAN_ROOM_TEST": "1"},
            clear_clean_room_env=True,
        )
        cp3 = self._run_cli(
            [CLI_CMD_ALIAS, "--simulate-bench-dry-run", "--json"],
            env_overrides={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
            clear_clean_room_env=True,
        )
        self.assertEqual(cp1.returncode, 0)
        self.assertEqual(cp2.returncode, 0)
        self.assertEqual(cp3.returncode, 0)
        self.assertEqual(
            json.loads(cp1.stdout)["report_sha256"],
            json.loads(cp2.stdout)["report_sha256"],
        )
        self.assertEqual(
            json.loads(cp1.stdout)["report_sha256"],
            json.loads(cp3.stdout)["report_sha256"],
        )

    def test_101_cli_same_st_dev_physical_receipt_paths_blocked_rc2(self) -> None:
        sim = build_simulated_phase368_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "FX3RCPT1_A.bin"
            pb = Path(td) / "FX3RCPT1_B.bin"
            pa.write_bytes(sim["receipt_a_bytes"])
            pb.write_bytes(sim["receipt_b_bytes"])
            cp = self._run_cli(
                [
                    CLI_CMD_ALIAS,
                    "--force-clean-room",
                    "--receipt-a",
                    str(pa),
                    "--receipt-b",
                    str(pb),
                    "--body-serial",
                    sim["body_serial"],
                    "--emmc-cid",
                    sim["emmc_cid"],
                    "--json",
                ],
                clear_clean_room_env=True,
            )
            # Same tmpdir filesystem shares st_dev -> fails closed rc=2 unless distinct st_dev!
            self.assertEqual(cp.returncode, 2)
            data = json.loads(cp.stdout)
            self.assertFalse(data["tier0_receipt_verified"])

    def test_102_cli_dci4k_2400p_sq_48fps_passes_rc0(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--shoot-mode",
                "S_AND_Q",
                "--file-format",
                "XAVC_S_I_DCI_4K",
                "--rec-frame-rate-fps",
                "24.0",
                "--sq-frame-rate-fps",
                "48",
                "--playback-clip-fps",
                "24.0",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertTrue(data["check_group_a"]["cross_2400p_reboot_triggered"])
        self.assertTrue(data["check_group_a"]["playback_2400p_isolated"])

    def test_103_cli_sq_xavc_s_hd_120fps_v60_passes_rc0(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--shoot-mode",
                "S_AND_Q",
                "--file-format",
                "XAVC_S_HD",
                "--sq-frame-rate-fps",
                "120",
                "--media-card-speed",
                "SDXC_V60",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["check_group_a"]["required_min_card_speed"], "SDXC_V60")

    def test_104_cli_shutter_angle_and_steadyshot_active_pass_rc0(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--shutter-mode",
                "ANGLE",
                "--shutter-angle-value",
                "180.0",
                "--steadyshot-movie",
                "ACTIVE",
                "--frame-rate-fps",
                "23.98",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data["check_group_c"]["effective_steadyshot_movie"], "ACTIVE")
        self.assertTrue(data["check_group_c"]["catalyst_gyro_rtmd_available"])

    def test_105_cli_srt_caller_usb_lan_airplane_mode_passes_rc0(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--streaming-active",
                "--streaming-protocol",
                "SRT",
                "--srt-role",
                "SRT_CALLER",
                "--streaming-codec",
                "H265",
                "--streaming-transport",
                "USB_LAN",
                "--airplane-mode",
                "ON",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        data = json.loads(cp.stdout)
        self.assertTrue(data["check_group_d"]["usb_lan_bypasses_airplane_mode"])
        self.assertEqual(data["rf_packets_transmitted"], 0)

    def test_106_cli_vpg400_proxy_trigger_on_vpg200_returns_rc2_blocked(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--shoot-mode",
                "S_AND_Q",
                "--file-format",
                "XAVC_S_I_4K",
                "--sq-frame-rate-fps",
                "120",
                "--record-setting-mbps",
                "1200",
                "--proxy-recording-enabled",
                "--media-card-speed",
                "CFEA_VPG200",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 2)
        data = json.loads(cp.stdout)
        self.assertTrue(data["check_group_a"]["vpg400_proxy_threshold_triggered"])
        self.assertEqual(data["check_group_a"]["required_min_card_speed"], "CFEA_VPG400")

    def test_107_cli_photo_capture_dci4k_blocked_returns_rc2_blocked(self) -> None:
        cp = self._run_cli(
            [
                CLI_CMD_ALIAS,
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--source-file-format",
                "XAVC_S_I_DCI_4K",
                "--photo-capture-requested",
                "--json",
            ],
            clear_clean_room_env=True,
        )
        self.assertEqual(cp.returncode, 2)
        data = json.loads(cp.stdout)
        self.assertTrue(data["check_group_d"]["photo_capture_dci4k_blocked"])

    def test_108_zero_pycache_emission_inside_fx6_closure(self) -> None:
        closure_pkg = REPO_ROOT / "outputs/fx6-on-fx3-closure/fx6_closure"
        pyc_files = list(closure_pkg.rglob("*.pyc"))
        self.assertEqual(pyc_files, [], msg=f"Unexpected .pyc files found: {pyc_files}")


if __name__ == "__main__":
    unittest.main()
