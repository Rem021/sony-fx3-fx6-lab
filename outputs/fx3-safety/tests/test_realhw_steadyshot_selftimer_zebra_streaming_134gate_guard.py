"""Phase 305 (Wave-57, 134/134 Safety Gates Milestone!) Dual-Mode Unit Tests (86 tests) for
`fx3_safety.realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard`:

- Gate `G133` (`GATE_G133_STEADYSHOT_IBIS_4LOCK_47FL_VS_DYNAMIC_FX6_AND_MOVIE_SELFTIMER_DORMANT_GUARD`):
  - `MENU -> (Shooting) -> [Image Stabilization]` (`_g.uxc 0x6214`): Movie `[SteadyShot]`
    (`Active` / `Standard` / `Off`, ~`1.104x` crop & `[Distortion Comp.] = Auto`), Still
    `[SteadyShot]` (`On` / `Off`), `[SteadyShot Adjust.]` (`Auto` / `Manual`), and exact
    **47-entry `[Focal Length]` table** (`8mm..1000mm`). All 4 reset by `[Camera Settings Reset]`.
  - Empirically enforces ALL **4 `[Active]` lockout conditions**: (a) Movie Rec Frame Rate
    `>= 119.88p / 100p`, (b) S&Q Frame Rate `>= 120fps / 100fps`, (c) HDMI RAW Output = `On`,
    and (d) `[De-Squeeze Display]` (`1.3x..2.0x`), rejecting dormant `[Dynamic active]`
    (`_f.uxc 0x741c`, `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID` -> `EOPNOTSUPP=95`) and contrasting
    IBIS-less `ILME-FX6` (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`, lens OSS Off for Catalyst).
  - Still vs Movie `[Self-timer]` hardware reality split: rejects dormant Movie `[Self-timer]`
    (`BKID_APP_setting_movie_self_timer`, `_f.uxc 0x7192 Rec Start delay`, `Single Burst`,
    `Self-portrait 3-sec` -> `EOPNOTSUPP=95`) while validating Still-only `[Self-timer(Single)]`,
    exact 6 combinations of `[Self-timer(Cont)]`, `[Selftimer during Bracket]`, front #8
    self-timer lamp (distinct from REC tally), and `Initialize`-only `[Audio signals]`
    suppression under `[Silent Mode]` / HDMI audio during movie rec.
- Gate `G134` (`GATE_G134_ZEBRA_CUSTOM12_PEAKING_4COLOR_VS_FX6_3WAY_AND_STREAMING_FTP_ZERORF_SLOT1_FIREWALL`):
  - FX3 `[Zebra Display]` & `[Zebra Level]` (`70..100+` + `Custom1 Std+Range 0..109% +- 1..10%`
    + `Custom2 Lower Limit 0..109+`, `S-Log3` `41%/61%/~94%`, `[Display LUT] = On` post-LUT
    measurement) and 4-color `[Peaking]` (`Red/Yellow/Blue/White`), `Initialize`-only &
    clean-HDMI isolated, contrasted with `ILME-FX6` strict 3-way `Off/Zebra1/Zebra2` selector
    (rejecting simultaneous `Both`) & FX6 `B&W/Red/Yellow/Blue` Peaking.
  - `[Network Streaming]` (`RTMP/RTMPS/SRT`, `59.94p/50p/29.97p/25p` valid vs `23.98p/24p`
    rejected, bitrate `<= 38 Mbps`, internal 4K rec locked out during `4K` or `2K 59.94p/50p`
    streaming), `[FTP Transfer Func.]`, and `[Reset Network Set.]` preserving `[Airplane Mode] = On`.
  - CRITICAL BENCH FIREWALL: `[Airplane Mode] = On` zero-RF lock (`0` wireless packets,
    `rf_nvs_p12_p13_writes_permitted == False`, wired `USB-LAN` allowed) + fail-closed
    `EROFS=30` / `EBUSY=16` on `Slot-1` Tier-0 Vault whenever `[Movie Rec During Streaming] = Enable`
    or FTP marker writes target `Slot 1` (`slot1_data_sector_writes == 0`).
- Unified `134`-Gate Milestone Master Preflight (`evaluate_134gate_preflight` / `verify-134-gates`):
  - `131/134` offline and `134/134` under `--simulate-bench-dry-run` with all hardware
    write/attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard import (
    Master132GateReport,
    STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
)
from fx3_safety.realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard import (
    AIRPLANE_MODE_MENU_PATH_G134,
    ALLOWED_AUDIO_SIGNALS_MODES_G133,
    ALLOWED_DESQUEEZE_RATIOS_G133,
    ALLOWED_DRIVE_MODES_G133,
    ALLOWED_MOVIE_STEADYSHOT_MODES_G133,
    ALLOWED_PEAKING_COLORS_FX3_G134,
    ALLOWED_PEAKING_LEVELS_G134,
    ALLOWED_SELF_TIMER_CONT_OPTIONS_G133,
    ALLOWED_SELF_TIMER_SINGLE_OPTIONS_G133,
    ALLOWED_SELFTIMER_BRACKET_OPTIONS_G133,
    ALLOWED_STEADYSHOT_ADJUST_MODES_G133,
    ALLOWED_STILL_STEADYSHOT_MODES_G133,
    ALLOWED_STREAM_FRAME_RATES_G134,
    ALLOWED_STREAM_PROTOCOLS_G134,
    ALLOWED_STREAM_RESOLUTIONS_G134,
    ALLOWED_ZEBRA_LEVEL_PRESETS_G134,
    AUDIO_SIGNALS_DEFAULT_G133,
    AUDIO_SIGNALS_OFF_G133,
    AUDIO_SIGNALS_ON_G133,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DESQUEEZE_1_3X_G133,
    DESQUEEZE_1_5X_G133,
    DESQUEEZE_1_65X_G133,
    DESQUEEZE_1_8X_G133,
    DESQUEEZE_2_0X_G133,
    DESQUEEZE_OFF_1_0X_G133,
    DISALLOWED_STREAM_FRAME_RATES_G134,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE305,
    DONOR_CHECK_MAX_SECONDS_PHASE305,
    DORMANT_DYNAMIC_ACTIVE_TRAPS_G133,
    DORMANT_SELFTIMER_TRAPS_G133,
    DRIVE_MODE_DEFAULT_G133,
    DRIVE_MODE_SELF_TIMER_CONT_G133,
    DRIVE_MODE_SELF_TIMER_SINGLE_G133,
    DRIVE_MODE_SINGLE_SHOOTING_G133,
    EBUSY_ERRNO_PHASE305,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE305,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE305,
    EROFS_ERRNO_PHASE305,
    FRONT_SELFTIMER_LAMP_MODULE_G133,
    FX3_DEFAULT_FW_VERSION_PHASE305,
    FX3_HELP_GUIDE_CODE_PHASE305,
    FX3_MODEL_ID_PHASE305,
    FX3_MODEL_NAME_PHASE305,
    FX6_DELAY_OR_TIMELAPSE_MECHANISMS_G133,
    FX6_DORMANT_STREAMING_SYMBOLS_G134,
    FX6_MODEL_NAME_PHASE305,
    FX6_PEAKING_COLORS_G134,
    FX6_STEADYSHOT_ELF_SYMBOL_G133,
    FX6_ZEBRA_3WAY_MODES_G134,
    G133,
    G133_GATE_CODE,
    G133_GATE_ID,
    G134,
    G134_GATE_CODE,
    G134_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    IMAGE_STABILIZATION_MENU_PATH_G133,
    MEDIA_SLOT_1_PHASE305,
    MEDIA_SLOT_2_PHASE305,
    MOVIE_REC_DURING_STREAMING_DEFAULT_G134,
    MOVIE_REC_DURING_STREAMING_DISABLE_G134,
    MOVIE_REC_DURING_STREAMING_ENABLE_G134,
    MOVIE_STEADYSHOT_ACTIVE_CROP_APPROX_G133,
    MOVIE_STEADYSHOT_ACTIVE_G133,
    MOVIE_STEADYSHOT_DEFAULT_G133,
    MOVIE_STEADYSHOT_OFF_G133,
    MOVIE_STEADYSHOT_STANDARD_G133,
    NET_IFACE_BLE_G134,
    NET_IFACE_USB_LAN_G134,
    NET_IFACE_USB_TETHERING_G134,
    NET_IFACE_WIFI_G134,
    NET_OP_FTP_TRANSFER_G134,
    NET_OP_NONE_G134,
    NET_OP_STREAM_ONLY_G134,
    NET_OP_STREAM_WITH_INTERNAL_REC_G134,
    NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
    NETWORK_STREAMING_MENU_PATH_G134,
    PEAKING_COLOR_BLUE_G134,
    PEAKING_COLOR_DEFAULT_G134,
    PEAKING_COLOR_RED_G134,
    PEAKING_COLOR_WHITE_G134,
    PEAKING_COLOR_YELLOW_G134,
    PEAKING_LEVEL_HIGH_G134,
    PEAKING_LEVEL_LOW_G134,
    PEAKING_LEVEL_MID_G134,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE305,
    PINNED_FX6_APPFW_SLICES_PHASE305,
    PINNED_PHASE305_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
    RESET_ACTION_INITIALIZE_PHASE305,
    RESET_ACTION_NONE_PHASE305,
    RESET_ACTION_RESET_NETWORK_SET_PHASE305,
    SELF_TIMER_CONT_10S_3IMG_G133,
    SELF_TIMER_CONT_10S_5IMG_G133,
    SELF_TIMER_CONT_2S_3IMG_G133,
    SELF_TIMER_CONT_2S_5IMG_G133,
    SELF_TIMER_CONT_5S_3IMG_G133,
    SELF_TIMER_CONT_5S_5IMG_G133,
    SELF_TIMER_SINGLE_10S_G133,
    SELF_TIMER_SINGLE_2S_G133,
    SELF_TIMER_SINGLE_5S_G133,
    SELFTIMER_BRACKET_10S_G133,
    SELFTIMER_BRACKET_2S_G133,
    SELFTIMER_BRACKET_5S_G133,
    SELFTIMER_BRACKET_OFF_G133,
    SHOOT_MODE_MOVIE_PHASE305,
    SHOOT_MODE_SQ_PHASE305,
    SHOOT_MODE_STILL_PHASE305,
    SLOG3_18PCT_GREY_IRE_G134,
    SLOG3_90PCT_WHITE_IRE_G134,
    SLOG3_CLIPPING_IRE_APPROX_G134,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION,
    STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION,
    STATUS_BLOCKED_G133_TELEMETRY_INVALID,
    STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION,
    STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION,
    STATUS_BLOCKED_G134_TELEMETRY_INVALID,
    STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY,
    STATUS_VERIFIED_G133,
    STATUS_VERIFIED_G134,
    STATUS_VERIFIED_SAFE,
    STEADYSHOT_47_FOCAL_LENGTHS_MM_G133,
    STEADYSHOT_ADJUST_AUTO_G133,
    STEADYSHOT_ADJUST_DEFAULT_G133,
    STEADYSHOT_ADJUST_MANUAL_G133,
    STEADYSHOT_FOCAL_LENGTH_DEFAULT_MM_G133,
    STILL_STEADYSHOT_DEFAULT_G133,
    STILL_STEADYSHOT_OFF_G133,
    STILL_STEADYSHOT_ON_G133,
    STREAM_MAX_BITRATE_MBPS_G134,
    STREAM_PROTO_RTMP_G134,
    STREAM_PROTO_RTMPS_G134,
    STREAM_PROTO_SRT_G134,
    STREAM_RES_2K_G134,
    STREAM_RES_4K_G134,
    STREAM_RES_HD_1080_G134,
    STREAM_RES_HD_720_G134,
    USB_PACKETS_TRANSMITTED,
    ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134,
    ZEBRA_CUSTOM_TYPE_STD_RANGE_G134,
    ZEBRA_LEVEL_DEFAULT_G134,
    audit_phase305_donor_contracts,
    compute_steadyshot_selftimer_matrix,
    compute_zebra_peaking_streaming_matrix,
    evaluate_134_master_safety_gates,
    evaluate_134gate_preflight,
    evaluate_g133_steadyshot_selftimer_guard,
    evaluate_g134_zebra_streaming_firewall_guard,
    main as module_main,
    resolve_fx3_steadyshot_selftimer_state,
    resolve_fx3_zebra_peaking_streaming_state,
    run_134_gate_preflight,
    verify_steadyshot_and_selftimer_guard,
    verify_zebra_peaking_streaming_firewall_guard,
)


def _make_stub_master132(
    *, dry_run: bool = False, all_g13_132_ok: bool = True
) -> Master132GateReport:
    gates = []
    for i in range(1, 133):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_132_ok or i <= 12)
        gates.append(
            {
                "gate_id": gid,
                "gate_code": f"STUB_{gid}",
                "status": "STATUS_VERIFIED_SAFE" if passed else "PENDING_PHYSICAL_TIER0",
                "passed": passed,
                "evidence": "stub",
                "violation_codes": [],
            }
        )
    g01_12 = 12 if dry_run else 9
    g13_130 = 118 if all_g13_132_ok else 0
    g131_132 = 2 if all_g13_132_ok else 0
    total = g01_12 + g13_130 + g131_132
    return Master132GateReport(
        schema="stub_132",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_129_gates_verified=all_g13_132_ok,
        all_132_gates_verified=(dry_run and all_g13_132_ok),
        g13_to_g132_all_passed=all_g13_132_ok,
        g131_to_g132_all_passed=all_g13_132_ok,
        h0_h1_trial_entry_allowed=all_g13_132_ok,
        status=(
            "VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0"
        ),
        agent_auto_flash_blocked=True,
        human_hardware_attach_token=False,
        el3_payload_transmit_authorized=False,
        spi_nor_write_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        physical_flash_auto_exec_authorized=False,
        cross_model_flash_authorized=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=0,
        technical_gates_passed=total,
        summary={
            "g01_to_g12_verified": g01_12,
            "g13_to_g130_verified": g13_130,
            "g131_to_g132_verified": g131_132,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_130_report={},
        g131_result={},
        g132_result={},
        errors=(),
        warnings=(),
    )


class TestPackageExportsAndDonorAudit(unittest.TestCase):
    def test_01_package_exports_phase305_symbols(self) -> None:
        self.assertIs(fx3_safety.evaluate_134gate_preflight, evaluate_134gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_g133_steadyshot_selftimer_guard,
            evaluate_g133_steadyshot_selftimer_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g134_zebra_streaming_firewall_guard,
            evaluate_g134_zebra_streaming_firewall_guard,
        )
        self.assertEqual(fx3_safety.G133, "G133")
        self.assertEqual(fx3_safety.G134, "G134")
        self.assertIn("evaluate_134gate_preflight", fx3_safety.__all__)
        self.assertIn("evaluate_g133_steadyshot_selftimer_guard", fx3_safety.__all__)
        self.assertIn("evaluate_g134_zebra_streaming_firewall_guard", fx3_safety.__all__)

    def test_02_immutable_redlines_hard_locked_false_and_zero(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_frozen_dataclasses_and_schema_constants(self) -> None:
        self.assertEqual(
            REALHW_STEADYSHOT_SELFTIMER_ZEBRA_STREAMING_134GATE_SCHEMA,
            "realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard_v1",
        )
        res = verify_steadyshot_and_selftimer_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res.valid = False  # type: ignore[misc]
        res2 = verify_zebra_peaking_streaming_firewall_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res2.valid = False  # type: ignore[misc]

    def test_04_donor_audit_clean_room_forced_under_budget(self) -> None:
        t0 = time.perf_counter()
        audit = audit_phase305_donor_contracts(force_clean_room=True)
        dt = time.perf_counter() - t0
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_TOUCH")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE305 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE305
        )
        self.assertLessEqual(dt, budget)

    def test_05_donor_audit_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE305: "1"}):
            audit = audit_phase305_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_env_fx3_fx6_force_clean_room_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            audit = audit_phase305_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_absent_donor_fallback_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_paths = mock.Mock()
            fake_paths.work_root = Path(td)
            with mock.patch(
                "fx3_safety.realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                audit = audit_phase305_donor_contracts(
                    repo_root=Path(td),
                    force_clean_room=False,
                )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")

    def test_08_donor_audit_real_o_rdonly_or_clean_room_dual_mode(self) -> None:
        t0 = time.perf_counter()
        audit = audit_phase305_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        dt = time.perf_counter() - t0
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE305 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else 5.0
        )
        self.assertLessEqual(dt, budget)
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 11)
            self.assertEqual(len(audit.checked_markers), 11)
            self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE305), 50)
            self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE305), 15)

    def test_09_donor_audit_detects_missing_or_tampered_file_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            sample = fake_root / "fake.uxc"
            sample.write_bytes(b"TAMPERED_CONTENT")
            bad_specs = {
                "fx3_fake": (
                    "FX3",
                    "fake.uxc",
                    999,
                    "0" * 64,
                    (b"EXPECTED_TOKEN",),
                    "Tamper test",
                )
            }
            audit = audit_phase305_donor_contracts(
                work_root=fake_root,
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE305_DONOR_INTEGRITY)
            self.assertGreaterEqual(len(audit.missing_markers), 3)

    def test_10_donor_specs_contain_all_11_wave57_artifacts(self) -> None:
        expected_keys = {
            "fx3_appfw_so",
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
            "fx3_string_english_uxc",
            "fx3_string_english_g_uxc",
            "fx3_bk4_bin",
            "fx6_appfw_so",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        }
        self.assertEqual(set(PINNED_PHASE305_DONOR_SPECS.keys()), expected_keys)


class TestGateG133SteadyShotAndSelfTimerGuard(unittest.TestCase):
    def test_11_g133_default_nominal_fx3_movie_standard_passes(self) -> None:
        res = verify_steadyshot_and_selftimer_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G133)
        self.assertEqual(res.image_stabilization_menu_path, IMAGE_STABILIZATION_MENU_PATH_G133)
        self.assertTrue(res.fx3_has_5axis_ibis)
        self.assertFalse(res.fx6_has_5axis_ibis)
        self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)
        self.assertEqual(res.effective_still_steadyshot, STILL_STEADYSHOT_ON_G133)
        self.assertEqual(res.effective_steadyshot_adjust, STEADYSHOT_ADJUST_AUTO_G133)
        self.assertEqual(res.effective_focal_length_mm, 8)
        self.assertEqual(res.focal_length_table_count, 47)
        self.assertAlmostEqual(res.movie_active_crop_approx, 1.104, places=3)

    def test_12_g133_active_allowed_under_normal_2398p_and_forces_distortion_comp_auto(self) -> None:
        res = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE305,
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            movie_rec_frame_rate="23.98p",
            sq_frame_rate="24fps",
            hdmi_raw_output_on=False,
            de_squeeze_ratio=DESQUEEZE_OFF_1_0X_G133,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_ACTIVE_G133)
        self.assertFalse(res.movie_active_locked_out)
        self.assertTrue(res.distortion_comp_forced_auto)
        self.assertEqual(res.movie_active_crop_approx, MOVIE_STEADYSHOT_ACTIVE_CROP_APPROX_G133)

    def test_13_g133_active_lockout_condition_1_movie_rec_11988p_100p(self) -> None:
        for fps in ("119.88p", "100p", "120p"):
            res = verify_steadyshot_and_selftimer_guard(
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                movie_rec_frame_rate=fps,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.movie_active_locked_out)
            self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)
            self.assertFalse(res.distortion_comp_forced_auto)

            bad = verify_steadyshot_and_selftimer_guard(
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                movie_rec_frame_rate=fps,
                force_active_under_lockout=True,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION,
            )
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE305)

    def test_14_g133_active_lockout_condition_2_sq_120fps_100fps_240fps(self) -> None:
        for sqfps in ("100fps", "120fps", "200fps", "240fps"):
            res = verify_steadyshot_and_selftimer_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE305,
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                sq_frame_rate=sqfps,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.movie_active_locked_out)
            self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)

            bad = verify_steadyshot_and_selftimer_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE305,
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                sq_frame_rate=sqfps,
                force_active_under_lockout=True,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE305)

    def test_15_g133_active_lockout_condition_3_hdmi_raw_output_on(self) -> None:
        res = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            hdmi_raw_output_on=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.movie_active_locked_out)
        self.assertIn("hdmi_raw_output=On", res.movie_active_lockout_reasons)
        self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)

        bad = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            hdmi_raw_output_on=True,
            claimed_active_allowed_under_lockout=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION,
        )

    def test_16_g133_active_lockout_condition_4_de_squeeze_1_3x_to_2_0x(self) -> None:
        for ratio in (
            DESQUEEZE_1_3X_G133,
            DESQUEEZE_1_5X_G133,
            DESQUEEZE_1_65X_G133,
            DESQUEEZE_1_8X_G133,
            DESQUEEZE_2_0X_G133,
        ):
            res = verify_steadyshot_and_selftimer_guard(
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                de_squeeze_ratio=ratio,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.movie_active_locked_out)
            self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)

            bad = verify_steadyshot_and_selftimer_guard(
                requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
                de_squeeze_ratio=ratio,
                force_active_under_lockout=True,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE305)

    def test_17_g133_dormant_dynamic_active_and_hybrid_traps_rejected_eopnotsupp(self) -> None:
        for trap in DORMANT_DYNAMIC_ACTIVE_TRAPS_G133:
            res = verify_steadyshot_and_selftimer_guard(
                requested_dormant_steadyshot_symbol=trap,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_dynamic_active_blocked)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE305)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION,
            )

        res2 = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot="Dynamic active"
        )
        self.assertFalse(res2.valid)
        self.assertEqual(res2.block_errno, 95)

    def test_18_g133_exact_47_entry_focal_length_table_validated(self) -> None:
        self.assertEqual(len(STEADYSHOT_47_FOCAL_LENGTHS_MM_G133), 47)
        self.assertEqual(STEADYSHOT_47_FOCAL_LENGTHS_MM_G133[0], 8)
        self.assertEqual(STEADYSHOT_47_FOCAL_LENGTHS_MM_G133[-1], 1000)
        for fl in STEADYSHOT_47_FOCAL_LENGTHS_MM_G133:
            res = verify_steadyshot_and_selftimer_guard(
                requested_steadyshot_adjust=STEADYSHOT_ADJUST_MANUAL_G133,
                requested_focal_length_mm=fl,
            )
            self.assertTrue(res.valid, msg=f"FL={fl} failed")
            self.assertEqual(res.effective_focal_length_mm, fl)

    def test_19_g133_out_of_table_and_bool_focal_length_rejected(self) -> None:
        for bad_fl in (7, 22, 23, 26, 38, 65, 95, 110, 700, 1200, True):
            res = verify_steadyshot_and_selftimer_guard(
                requested_steadyshot_adjust=STEADYSHOT_ADJUST_MANUAL_G133,
                requested_focal_length_mm=bad_fl,  # type: ignore[arg-type]
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION,
            )

    def test_20_g133_fx6_ibis_less_oss_off_for_catalyst_crosswire_guard(self) -> None:
        self.assertEqual(
            FX6_STEADYSHOT_ELF_SYMBOL_G133, "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"
        )
        ok_fx6 = verify_steadyshot_and_selftimer_guard(
            target_model=FX6_MODEL_NAME_PHASE305,
            fx6_lens_oss_on=False,
            fx6_catalyst_stabilization_requested=True,
        )
        self.assertTrue(ok_fx6.valid)

        for bad_kw in (
            {"claimed_fx6_has_body_ibis": True},
            {"claimed_fx6_catalyst_compatible_with_oss_on": True},
            {"fx6_lens_oss_on": True, "fx6_catalyst_stabilization_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE305, "requested_steadyshot_adjust": "Manual"},
            {"target_model": FX6_MODEL_NAME_PHASE305, "requested_focal_length_mm": 50},
        ):
            bad = verify_steadyshot_and_selftimer_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G133_FOCAL_LENGTH_OR_FX6_IBIS_CROSSWIRE_VIOLATION,
            )

    def test_21_g133_clear_image_zoom_coexists_with_steadyshot_and_locks_high_fps_raw(self) -> None:
        ok = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE305,
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            movie_rec_frame_rate="59.94p",
            clear_image_zoom_on=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.clear_image_zoom_available)
        self.assertTrue(ok.clear_image_zoom_coexists_with_steadyshot)

        for bad_kw in (
            {
                "shoot_mode": SHOOT_MODE_MOVIE_PHASE305,
                "movie_rec_frame_rate": "119.88p",
                "clear_image_zoom_on": True,
            },
            {
                "shoot_mode": SHOOT_MODE_SQ_PHASE305,
                "sq_frame_rate": "120fps",
                "clear_image_zoom_on": True,
            },
            {
                "shoot_mode": SHOOT_MODE_STILL_PHASE305,
                "still_raw_capture": True,
                "clear_image_zoom_on": True,
            },
            {"claimed_ciz_allowed_in_high_fps_or_raw": True},
            {"claimed_ciz_disables_steadyshot": True},
        ):
            bad = verify_steadyshot_and_selftimer_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION,
            )

    def test_22_g133_dormant_movie_selftimer_and_self_portrait_rejected_eopnotsupp(self) -> None:
        for trap in DORMANT_SELFTIMER_TRAPS_G133:
            res = verify_steadyshot_and_selftimer_guard(
                requested_dormant_selftimer_symbol=trap
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_movie_selftimer_blocked)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE305)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION,
            )

        for mode in (SHOOT_MODE_MOVIE_PHASE305, SHOOT_MODE_SQ_PHASE305):
            bad = verify_steadyshot_and_selftimer_guard(
                shoot_mode=mode,
                requested_drive_mode=DRIVE_MODE_SELF_TIMER_SINGLE_G133,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, 95)

    def test_23_g133_still_selftimer_single_all_3_durations_validated(self) -> None:
        self.assertEqual(
            ALLOWED_SELF_TIMER_SINGLE_OPTIONS_G133,
            (SELF_TIMER_SINGLE_10S_G133, SELF_TIMER_SINGLE_5S_G133, SELF_TIMER_SINGLE_2S_G133),
        )
        for dur in ALLOWED_SELF_TIMER_SINGLE_OPTIONS_G133:
            res = verify_steadyshot_and_selftimer_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE305,
                requested_drive_mode=DRIVE_MODE_SELF_TIMER_SINGLE_G133,
                requested_self_timer_single=dur,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_drive_mode, DRIVE_MODE_SELF_TIMER_SINGLE_G133)
            self.assertEqual(res.effective_self_timer_single, dur)
            self.assertTrue(res.front_selftimer_lamp_active)
            self.assertTrue(res.front_selftimer_lamp_distinct_from_rec_tally)

    def test_24_g133_still_selftimer_cont_all_6_combinations_validated(self) -> None:
        self.assertEqual(len(ALLOWED_SELF_TIMER_CONT_OPTIONS_G133), 6)
        for opt in (
            SELF_TIMER_CONT_10S_3IMG_G133,
            SELF_TIMER_CONT_10S_5IMG_G133,
            SELF_TIMER_CONT_5S_3IMG_G133,
            SELF_TIMER_CONT_5S_5IMG_G133,
            SELF_TIMER_CONT_2S_3IMG_G133,
            SELF_TIMER_CONT_2S_5IMG_G133,
        ):
            res = verify_steadyshot_and_selftimer_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE305,
                requested_drive_mode=DRIVE_MODE_SELF_TIMER_CONT_G133,
                requested_self_timer_cont=opt,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_self_timer_cont, opt)
            self.assertTrue(res.front_selftimer_lamp_active)

    def test_25_g133_selftimer_during_bracket_all_4_options_validated(self) -> None:
        self.assertEqual(
            ALLOWED_SELFTIMER_BRACKET_OPTIONS_G133,
            (
                SELFTIMER_BRACKET_OFF_G133,
                SELFTIMER_BRACKET_2S_G133,
                SELFTIMER_BRACKET_5S_G133,
                SELFTIMER_BRACKET_10S_G133,
            ),
        )
        for opt in ALLOWED_SELFTIMER_BRACKET_OPTIONS_G133:
            res = verify_steadyshot_and_selftimer_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE305,
                requested_selftimer_during_bracket=opt,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_selftimer_during_bracket, opt)

    def test_26_g133_audio_signals_suppression_silent_mode_and_hdmi_audio(self) -> None:
        s1 = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE305,
            silent_mode_on=True,
            requested_audio_signals=AUDIO_SIGNALS_ON_G133,
        )
        self.assertTrue(s1.valid)
        self.assertTrue(s1.audio_signals_suppressed)
        self.assertEqual(s1.effective_audio_signals, AUDIO_SIGNALS_OFF_G133)

        s2 = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE305,
            hdmi_audio_during_movie_rec=True,
            requested_audio_signals=AUDIO_SIGNALS_ON_G133,
        )
        self.assertTrue(s2.valid)
        self.assertTrue(s2.audio_signals_suppressed)
        self.assertEqual(s2.effective_audio_signals, AUDIO_SIGNALS_OFF_G133)

    def test_27_g133_camera_settings_reset_vs_initialize_persistence(self) -> None:
        cam_rst = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE305,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
            requested_movie_steadyshot=MOVIE_STEADYSHOT_OFF_G133,
            requested_still_steadyshot=STILL_STEADYSHOT_OFF_G133,
            requested_steadyshot_adjust=STEADYSHOT_ADJUST_MANUAL_G133,
            requested_focal_length_mm=85,
            requested_drive_mode=DRIVE_MODE_SELF_TIMER_SINGLE_G133,
            requested_self_timer_single=SELF_TIMER_SINGLE_2S_G133,
            requested_self_timer_cont=SELF_TIMER_CONT_5S_5IMG_G133,
            requested_selftimer_during_bracket=SELFTIMER_BRACKET_10S_G133,
            requested_audio_signals=AUDIO_SIGNALS_OFF_G133,
        )
        self.assertTrue(cam_rst.valid)
        self.assertEqual(cam_rst.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)
        self.assertEqual(cam_rst.effective_still_steadyshot, STILL_STEADYSHOT_ON_G133)
        self.assertEqual(cam_rst.effective_steadyshot_adjust, STEADYSHOT_ADJUST_AUTO_G133)
        self.assertEqual(cam_rst.effective_focal_length_mm, 8)
        self.assertEqual(cam_rst.effective_drive_mode, DRIVE_MODE_SINGLE_SHOOTING_G133)
        self.assertEqual(cam_rst.effective_selftimer_during_bracket, SELFTIMER_BRACKET_OFF_G133)
        self.assertEqual(cam_rst.effective_audio_signals, AUDIO_SIGNALS_OFF_G133)
        self.assertTrue(cam_rst.audio_signals_survived_cam_reset)

        init_rst = verify_steadyshot_and_selftimer_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE305,
            requested_audio_signals=AUDIO_SIGNALS_OFF_G133,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_audio_signals, AUDIO_SIGNALS_ON_G133)

    def test_28_g133_front_lamp_audio_volume_and_fx6_myth_flags_blocked(self) -> None:
        self.assertIn("#8", FRONT_SELFTIMER_LAMP_MODULE_G133)
        self.assertEqual(
            FX6_DELAY_OR_TIMELAPSE_MECHANISMS_G133,
            ("Project > Picture Cache Rec", "Project > Interval Rec"),
        )
        for bad_kw in (
            {"claimed_fx3_supports_audio_signal_volume": True},
            {"claimed_audio_signals_resets_on_cam_reset": True},
            {"claimed_steadyshot_ignores_cam_reset": True},
            {"claimed_front_rec_tally_is_selftimer_lamp": True},
            {"claimed_fx6_has_still_selftimer_or_front_lamp": True},
        ):
            bad = verify_steadyshot_and_selftimer_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G133_SELFTIMER_LAMP_AUDIO_OR_RESET_VIOLATION
            )

    def test_29_g133_1296_state_matrix_holds(self) -> None:
        m = compute_steadyshot_selftimer_matrix()
        self.assertEqual(m["states_checked"], 1296)
        self.assertTrue(m["all_invariants_hold"])
        self.assertGreater(m["active_lockout_count"], 900)
        self.assertEqual(m["cam_reset_verified_count"], 648)
        self.assertEqual(m["audio_suppressed_count"], 648)

    def test_30_g133_normalization_aliases_and_resolver(self) -> None:
        s = resolve_fx3_steadyshot_selftimer_state(
            shoot_mode="Still",
            requested_movie_steadyshot="standard",
            requested_still_steadyshot="on",
            requested_steadyshot_adjust="manual",
            requested_focal_length_mm=50,
            de_squeeze_ratio="1.6x",
            requested_drive_mode="self-timer",
            requested_self_timer_single="5s",
            requested_self_timer_cont="2s 5img",
            requested_selftimer_during_bracket="2s",
            requested_audio_signals="off",
        )
        self.assertTrue(s["valid"])
        self.assertEqual(s["de_squeeze_ratio"], DESQUEEZE_1_65X_G133)
        self.assertEqual(s["effective_drive_mode"], DRIVE_MODE_SELF_TIMER_SINGLE_G133)
        self.assertEqual(s["effective_self_timer_single"], SELF_TIMER_SINGLE_5S_G133)
        self.assertEqual(s["effective_self_timer_cont"], SELF_TIMER_CONT_2S_5IMG_G133)
        self.assertEqual(s["effective_selftimer_during_bracket"], SELFTIMER_BRACKET_2S_G133)
        self.assertEqual(s["effective_audio_signals"], AUDIO_SIGNALS_OFF_G133)

    def test_31_g133_invalid_telemetry_and_bool_body_id_rejected(self) -> None:
        for bad_kw in (
            {"body_model_id": True},
            {"body_model_name": "ILCE-7M4"},
            {"help_guide_code": "ilc/9999"},
            {"shoot_mode": "Timelapse"},
            {"reset_action": "Reboot"},
            {"requested_movie_steadyshot": "HyperSmooth"},
            {"de_squeeze_ratio": "3.0x"},
            {"requested_drive_mode": "ContinuousHi+"},
            {"requested_audio_signals": True},
        ):
            bad = verify_steadyshot_and_selftimer_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G133_TELEMETRY_INVALID)

    def test_32_g133_evaluate_with_persistent_emmc_write_blocked(self) -> None:
        verdict, res = evaluate_g133_steadyshot_selftimer_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_33_g133_enums_and_gate_constants_complete(self) -> None:
        self.assertEqual(G133, "G133")
        self.assertEqual(G133_GATE_ID, "G133")
        self.assertEqual(
            ALLOWED_MOVIE_STEADYSHOT_MODES_G133, ("Active", "Standard", "Off")
        )
        self.assertEqual(ALLOWED_STILL_STEADYSHOT_MODES_G133, ("On", "Off"))
        self.assertEqual(ALLOWED_STEADYSHOT_ADJUST_MODES_G133, ("Auto", "Manual"))
        self.assertEqual(len(ALLOWED_DESQUEEZE_RATIOS_G133), 6)
        self.assertEqual(len(ALLOWED_DRIVE_MODES_G133), 3)
        self.assertEqual(ALLOWED_AUDIO_SIGNALS_MODES_G133, ("On", "Off"))


class TestGateG134ZebraPeakingStreamingAndFirewalls(unittest.TestCase):
    def test_34_g134_default_nominal_fx3_zebra_peaking_streaming_firewall_passes(self) -> None:
        res = verify_zebra_peaking_streaming_firewall_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G134)
        self.assertEqual(res.effective_airplane_mode, "On")
        self.assertEqual(res.wireless_packets_emitted, 0)
        self.assertFalse(res.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(res.rf_nvs_mutation_bytes, 0)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_35_g134_zebra_presets_custom1_and_custom2_ire_bounds(self) -> None:
        self.assertEqual(len(ALLOWED_ZEBRA_LEVEL_PRESETS_G134), 10)
        for lvl in ALLOWED_ZEBRA_LEVEL_PRESETS_G134:
            ok = verify_zebra_peaking_streaming_firewall_guard(
                requested_zebra_display="On",
                requested_zebra_level=lvl,
                custom1_standard_ire=0,
                custom1_range_ire=1,
                custom2_lower_limit_ire=109,
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_zebra_level, lvl)

        for bad_kw in (
            {"custom1_standard_ire": -1},
            {"custom1_standard_ire": 110},
            {"custom1_range_ire": 0},
            {"custom1_range_ire": 11},
            {"custom2_lower_limit_ire": -1},
            {"custom2_lower_limit_ire": 110},
            {"custom1_standard_ire": True},
        ):
            bad = verify_zebra_peaking_streaming_firewall_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION
            )

    def test_36_g134_slog3_ire_anchors_and_display_lut_post_lut_awareness(self) -> None:
        self.assertEqual(SLOG3_18PCT_GREY_IRE_G134, 41)
        self.assertEqual(SLOG3_90PCT_WHITE_IRE_G134, 61)
        self.assertEqual(SLOG3_CLIPPING_IRE_APPROX_G134, 94)

        res = verify_zebra_peaking_streaming_firewall_guard(
            log_shooting_on=True,
            display_lut_on=True,
            requested_zebra_display="On",
            requested_zebra_level="Custom2",
            custom2_lower_limit_ire=94,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.zebra_measures_post_lut_display)

        for bad_kw in (
            {"claimed_slog3_107_catches_clipping": True},
            {"claimed_zebra_ignores_display_lut": True},
            {"claimed_zebra_or_peaking_resets_on_cam_reset": True},
        ):
            bad = verify_zebra_peaking_streaming_firewall_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION
            )

    def test_37_g134_fx3_4color_peaking_all_levels_and_colors(self) -> None:
        self.assertEqual(
            ALLOWED_PEAKING_COLORS_FX3_G134,
            (
                PEAKING_COLOR_RED_G134,
                PEAKING_COLOR_YELLOW_G134,
                PEAKING_COLOR_BLUE_G134,
                PEAKING_COLOR_WHITE_G134,
            ),
        )
        self.assertEqual(
            ALLOWED_PEAKING_LEVELS_G134,
            (PEAKING_LEVEL_HIGH_G134, PEAKING_LEVEL_MID_G134, PEAKING_LEVEL_LOW_G134),
        )
        for lvl in ALLOWED_PEAKING_LEVELS_G134:
            for col in ALLOWED_PEAKING_COLORS_FX3_G134:
                res = verify_zebra_peaking_streaming_firewall_guard(
                    requested_peaking_display="On",
                    requested_peaking_level=lvl,
                    requested_peaking_color=col,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_peaking_level, lvl)
                self.assertEqual(res.effective_peaking_color, col)

        bad_bw = verify_zebra_peaking_streaming_firewall_guard(
            requested_peaking_color="B&W"
        )
        self.assertFalse(bad_bw.valid)
        self.assertEqual(bad_bw.status, STATUS_BLOCKED_G134_TELEMETRY_INVALID)

    def test_38_g134_fx6_3way_zebra_selector_blocks_both_and_clean_hdmi_leak(self) -> None:
        self.assertEqual(FX6_ZEBRA_3WAY_MODES_G134, ("Off", "Zebra1", "Zebra2"))
        self.assertEqual(FX6_PEAKING_COLORS_G134, ("B&W", "Red", "Yellow", "Blue"))
        for mode in FX6_ZEBRA_3WAY_MODES_G134:
            ok = verify_zebra_peaking_streaming_firewall_guard(
                target_model=FX6_MODEL_NAME_PHASE305,
                fx6_zebra_setting=mode,
                fx6_zebra1_aperture_ire=2,
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.fx6_zebra_3way_selector_only)
            self.assertTrue(ok.fx6_zebra_simultaneous_both_blocked)
            self.assertTrue(ok.zebra_isolated_from_clean_hdmi)
            self.assertTrue(ok.peaking_isolated_from_clean_hdmi)

        for bad_kw in (
            {"fx6_zebra_setting": "Both"},
            {"claimed_fx6_zebra_simultaneous_both": True},
            {"fx6_zebra1_aperture_ire": 1},
            {"fx6_zebra1_aperture_ire": 21},
            {"claimed_zebra_or_peaking_on_clean_hdmi": True},
        ):
            bad = verify_zebra_peaking_streaming_firewall_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION
            )

    def test_39_g134_zebra_peaking_survive_cam_reset_and_reset_on_initialize(self) -> None:
        cam_rst = verify_zebra_peaking_streaming_firewall_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE305,
            requested_zebra_display="On",
            requested_zebra_level="Custom1",
            requested_peaking_display="On",
            requested_peaking_level=PEAKING_LEVEL_HIGH_G134,
            requested_peaking_color=PEAKING_COLOR_BLUE_G134,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.zebra_and_peaking_survived_cam_reset)
        self.assertEqual(cam_rst.effective_zebra_display, "On")
        self.assertEqual(cam_rst.effective_zebra_level, "Custom1")
        self.assertEqual(cam_rst.effective_peaking_color, PEAKING_COLOR_BLUE_G134)

        init_rst = verify_zebra_peaking_streaming_firewall_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE305,
            requested_zebra_display="On",
            requested_zebra_level="Custom1",
            requested_peaking_display="On",
            requested_peaking_color=PEAKING_COLOR_BLUE_G134,
            bench_zero_rf_required=False,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_zebra_display, "Off")
        self.assertEqual(init_rst.effective_zebra_level, "70")
        self.assertEqual(init_rst.effective_peaking_display, "Off")
        self.assertEqual(init_rst.effective_peaking_color, PEAKING_COLOR_WHITE_G134)

        init_bench_blocked = verify_zebra_peaking_streaming_firewall_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE305,
            bench_zero_rf_required=True,
        )
        self.assertFalse(init_bench_blocked.valid)
        self.assertEqual(
            init_bench_blocked.status,
            STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
        )

    def test_40_g134_network_streaming_protocols_resolutions_and_fps_validated(self) -> None:
        self.assertEqual(
            ALLOWED_STREAM_PROTOCOLS_G134,
            (STREAM_PROTO_RTMP_G134, STREAM_PROTO_RTMPS_G134, STREAM_PROTO_SRT_G134),
        )
        self.assertEqual(
            ALLOWED_STREAM_RESOLUTIONS_G134,
            (
                STREAM_RES_4K_G134,
                STREAM_RES_2K_G134,
                STREAM_RES_HD_1080_G134,
                STREAM_RES_HD_720_G134,
            ),
        )
        for proto in ALLOWED_STREAM_PROTOCOLS_G134:
            for fps in ALLOWED_STREAM_FRAME_RATES_G134:
                res = verify_zebra_peaking_streaming_firewall_guard(
                    streaming_active=True,
                    streaming_protocol=proto,
                    streaming_resolution=STREAM_RES_HD_1080_G134,
                    streaming_frame_rate=fps,
                    streaming_bitrate_mbps=STREAM_MAX_BITRATE_MBPS_G134,
                    requested_net_interface=NET_IFACE_USB_LAN_G134,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.effective_streaming_active)
                self.assertTrue(res.sq_rec_blocked_by_stream)
                self.assertTrue(res.streaming_locks_movie_mode_and_disables_ftp_playback)

    def test_41_g134_streaming_rejects_2398p_24p_and_over_38mbps_and_fx6_dormant_qos(self) -> None:
        for bad_fps in DISALLOWED_STREAM_FRAME_RATES_G134:
            bad = verify_zebra_peaking_streaming_firewall_guard(
                streaming_active=True,
                streaming_frame_rate=bad_fps,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE305)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION
            )

        for bad_kw in (
            {"streaming_bitrate_mbps": 38.1},
            {"streaming_bitrate_mbps": 0.0},
            {"streaming_bitrate_mbps": True},
            {"claimed_network_resets_on_cam_reset": True},
            {"claimed_fx6_has_native_rtmp_srt_qos": True},
            {"fx6_dormant_rtmp_srt_qos_requested": True},
        ):
            bad = verify_zebra_peaking_streaming_firewall_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION
            )

    def test_42_g134_internal_4k_rec_lockout_during_4k_or_2k_5994p_50p_streaming(self) -> None:
        for sres, sfps in (
            (STREAM_RES_4K_G134, "29.97p"),
            (STREAM_RES_4K_G134, "25p"),
            (STREAM_RES_2K_G134, "59.94p"),
            (STREAM_RES_2K_G134, "50p"),
        ):
            ok_hd = verify_zebra_peaking_streaming_firewall_guard(
                streaming_active=True,
                streaming_resolution=sres,
                streaming_frame_rate=sfps,
                requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
                requested_internal_rec_resolution=STREAM_RES_HD_1080_G134,
                requested_target_slot=MEDIA_SLOT_2_PHASE305,
                requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            )
            self.assertTrue(ok_hd.valid)
            self.assertTrue(ok_hd.internal_4k_rec_blocked_by_stream)
            self.assertEqual(ok_hd.forced_internal_rec_frame_rate, sfps)

            bad_4k = verify_zebra_peaking_streaming_firewall_guard(
                streaming_active=True,
                streaming_resolution=sres,
                streaming_frame_rate=sfps,
                requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
                requested_internal_rec_resolution=STREAM_RES_4K_G134,
                requested_target_slot=MEDIA_SLOT_2_PHASE305,
                requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            )
            self.assertFalse(bad_4k.valid)
            self.assertEqual(
                bad_4k.status,
                STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION,
            )

        ok_2k_2997 = verify_zebra_peaking_streaming_firewall_guard(
            streaming_active=True,
            streaming_resolution=STREAM_RES_2K_G134,
            streaming_frame_rate="29.97p",
            requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
            requested_internal_rec_resolution=STREAM_RES_4K_G134,
            requested_target_slot=MEDIA_SLOT_2_PHASE305,
            requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
        )
        self.assertTrue(ok_2k_2997.valid)
        self.assertFalse(ok_2k_2997.internal_4k_rec_blocked_by_stream)

    def test_43_g134_reset_network_set_preserves_airplane_mode_on_vs_initialize(self) -> None:
        net_rst = verify_zebra_peaking_streaming_firewall_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE305,
            requested_airplane_mode="On",
            streaming_active=True,
            requested_ftp_transfer_func="On",
            requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
        )
        self.assertTrue(net_rst.valid)
        self.assertTrue(net_rst.reset_network_set_preserved_airplane_mode)
        self.assertEqual(net_rst.effective_airplane_mode, "On")
        self.assertFalse(net_rst.effective_streaming_active)
        self.assertEqual(net_rst.effective_ftp_transfer_func, "Off")
        self.assertEqual(
            net_rst.effective_movie_rec_during_streaming,
            MOVIE_REC_DURING_STREAMING_DISABLE_G134,
        )

        init_rst = verify_zebra_peaking_streaming_firewall_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE305,
            requested_airplane_mode="On",
            bench_zero_rf_required=False,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_airplane_mode, "Off")

    def test_44_g134_critical_bench_firewall_airplane_zero_rf_blocks_wifi_ble(self) -> None:
        self.assertIn("Airplane Mode", AIRPLANE_MODE_MENU_PATH_G134)
        self.assertIn("Network Streaming", NETWORK_STREAMING_MENU_PATH_G134)
        for iface in (NET_IFACE_WIFI_G134, NET_IFACE_BLE_G134):
            for op in (NET_OP_STREAM_ONLY_G134, NET_OP_FTP_TRANSFER_G134):
                bad = verify_zebra_peaking_streaming_firewall_guard(
                    requested_airplane_mode="On",
                    requested_net_interface=iface,
                    requested_network_op=op,
                )
                self.assertFalse(bad.valid)
                self.assertTrue(bad.airplane_zero_rf_firewall_blocked)
                self.assertEqual(bad.wireless_packets_emitted, 0)
                self.assertFalse(bad.rf_nvs_p12_p13_writes_permitted)
                self.assertEqual(bad.rf_nvs_mutation_bytes, 0)
                self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE305)
                self.assertEqual(
                    bad.status, STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION
                )

    def test_45_g134_critical_bench_firewall_zero_rf_blocks_airplane_off_and_rf_nvs_writes(self) -> None:
        bad_off = verify_zebra_peaking_streaming_firewall_guard(
            requested_airplane_mode="Off",
            bench_zero_rf_required=True,
        )
        self.assertFalse(bad_off.valid)
        self.assertEqual(
            bad_off.status, STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION
        )
        self.assertEqual(bad_off.wireless_packets_emitted, 0)

        bad_nvs = verify_zebra_peaking_streaming_firewall_guard(
            requested_airplane_mode="On",
            rf_nvs_write_requested=True,
        )
        self.assertFalse(bad_nvs.valid)
        self.assertFalse(bad_nvs.rf_nvs_p12_p13_writes_permitted)
        self.assertEqual(bad_nvs.rf_nvs_mutation_bytes, 0)

    def test_46_g134_wired_usb_lan_and_usb_tethering_allowed_under_airplane_mode(self) -> None:
        for iface in (NET_IFACE_USB_LAN_G134, NET_IFACE_USB_TETHERING_G134):
            ok = verify_zebra_peaking_streaming_firewall_guard(
                requested_airplane_mode="On",
                streaming_active=True,
                requested_net_interface=iface,
                requested_network_op=NET_OP_STREAM_ONLY_G134,
            )
            self.assertTrue(ok.valid)
            self.assertFalse(ok.airplane_zero_rf_firewall_blocked)
            self.assertEqual(ok.wireless_packets_emitted, 0)

    def test_47_g134_slot1_tier0_vault_blocks_rec_during_streaming_and_ftp_marker_erofs_30(self) -> None:
        bad_rec = verify_zebra_peaking_streaming_firewall_guard(
            streaming_active=True,
            requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
            requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            requested_target_slot=MEDIA_SLOT_1_PHASE305,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=False,
        )
        self.assertFalse(bad_rec.valid)
        self.assertTrue(bad_rec.slot1_vault_firewall_blocked)
        self.assertEqual(bad_rec.block_errno, EROFS_ERRNO_PHASE305)
        self.assertEqual(bad_rec.block_errno_name, "EROFS")
        self.assertEqual(bad_rec.slot1_data_sector_writes, 0)
        self.assertFalse(bad_rec.slot1_avf_info_mutated)
        self.assertEqual(
            bad_rec.status,
            STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )

        bad_ftp = verify_zebra_peaking_streaming_firewall_guard(
            requested_ftp_transfer_func="On",
            requested_network_op=NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
            requested_target_slot=MEDIA_SLOT_1_PHASE305,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(bad_ftp.valid)
        self.assertEqual(bad_ftp.block_errno, 30)
        self.assertEqual(bad_ftp.slot1_data_sector_writes, 0)

    def test_48_g134_slot1_write_protected_blocks_with_ebusy_16(self) -> None:
        bad = verify_zebra_peaking_streaming_firewall_guard(
            requested_network_op=NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
            requested_target_slot=MEDIA_SLOT_1_PHASE305,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=True,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.slot1_vault_firewall_blocked)
        self.assertEqual(bad.block_errno, EBUSY_ERRNO_PHASE305)
        self.assertEqual(bad.block_errno_name, "EBUSY")
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_49_g134_slot2_rec_during_streaming_and_ftp_marker_allowed_zero_slot1_writes(self) -> None:
        for op in (
            NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
        ):
            ok = verify_zebra_peaking_streaming_firewall_guard(
                streaming_active=True,
                requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
                requested_ftp_transfer_func="On",
                requested_net_interface=NET_IFACE_USB_LAN_G134,
                requested_network_op=op,
                requested_target_slot=MEDIA_SLOT_2_PHASE305,
                slot_1_contains_tier0_vault=True,
                slot_1_write_protected=True,
            )
            self.assertTrue(ok.valid)
            self.assertFalse(ok.slot1_vault_firewall_blocked)
            self.assertEqual(ok.slot1_data_sector_writes, 0)
            self.assertFalse(ok.slot1_avf_info_mutated)

    def test_50_g134_slot1_write_allowed_only_when_vault_absent_and_unlocked(self) -> None:
        ok = verify_zebra_peaking_streaming_firewall_guard(
            requested_network_op=NET_OP_WRITE_FTP_MARKER_TO_CARD_G134,
            requested_target_slot=MEDIA_SLOT_1_PHASE305,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=False,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.slot1_vault_firewall_blocked)

    def test_51_g134_576_state_matrix_holds(self) -> None:
        m = compute_zebra_peaking_streaming_matrix()
        self.assertEqual(m["states_checked"], 576)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["post_lut_zebra_count"], 288)
        self.assertEqual(m["stream_4k_rec_blocked_count"], 288)
        self.assertEqual(m["zero_rf_blocked_count"], 432)
        self.assertEqual(m["slot1_vault_blocked_count"], 96)
        self.assertEqual(m["cam_reset_persist_count"], 192)

    def test_52_g134_normalization_aliases_and_resolver(self) -> None:
        s = resolve_fx3_zebra_peaking_streaming_state(
            shoot_mode="S&Q",
            requested_zebra_display="on",
            requested_zebra_level="custom2",
            custom1_type="std",
            custom2_type="lower",
            requested_peaking_display="on",
            requested_peaking_level="low",
            requested_peaking_color="yellow",
            streaming_protocol="rtmps",
            streaming_resolution="1080p",
            requested_movie_rec_during_streaming="enable",
            requested_ftp_transfer_func="on",
            requested_airplane_mode="on",
            requested_net_interface="cdc-ncm",
            requested_target_slot="slot b",
        )
        self.assertTrue(s["valid"])
        self.assertEqual(s["effective_zebra_level"], "Custom2")
        self.assertEqual(s["custom1_type"], ZEBRA_CUSTOM_TYPE_STD_RANGE_G134)
        self.assertEqual(s["custom2_type"], ZEBRA_CUSTOM_TYPE_LOWER_LIMIT_G134)
        self.assertEqual(s["effective_peaking_color"], PEAKING_COLOR_YELLOW_G134)
        self.assertEqual(s["streaming_protocol"], STREAM_PROTO_RTMPS_G134)
        self.assertEqual(s["requested_net_interface"], NET_IFACE_USB_LAN_G134)
        self.assertEqual(s["requested_target_slot"], MEDIA_SLOT_2_PHASE305)

    def test_53_g134_invalid_telemetry_and_bool_body_id_rejected(self) -> None:
        for bad_kw in (
            {"body_model_id": False},
            {"body_model_name": "FX9"},
            {"requested_zebra_level": "107+"},
            {"custom1_type": "Invalid"},
            {"requested_peaking_level": "Ultra"},
            {"streaming_protocol": "RTSP"},
            {"streaming_resolution": "8K"},
            {"requested_net_interface": "Ethernet5G"},
            {"requested_network_op": "DropAllPackets"},
            {"requested_target_slot": "Slot 3"},
        ):
            bad = verify_zebra_peaking_streaming_firewall_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G134_TELEMETRY_INVALID)

    def test_54_g134_evaluate_with_persistent_emmc_write_blocked(self) -> None:
        verdict, res = evaluate_g134_zebra_streaming_firewall_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_55_g134_gate_constants_and_fx6_dormant_symbols_pinned(self) -> None:
        self.assertEqual(G134, "G134")
        self.assertEqual(G134_GATE_ID, "G134")
        self.assertIn("BKID_APP_RTMP_SETTINGS1", FX6_DORMANT_STREAMING_SYMBOLS_G134)
        self.assertIn("BKID_APP_SRT_SETTINGS1", FX6_DORMANT_STREAMING_SYMBOLS_G134)
        self.assertIn("QoS Streaming", FX6_DORMANT_STREAMING_SYMBOLS_G134)


class TestUnified134GateEngineAndCli(unittest.TestCase):
    def test_56_stub_134gate_offline_131_of_134(self) -> None:
        rep = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=False),
        )
        self.assertEqual(rep.summary["total_gates"], 134)
        self.assertEqual(rep.summary["verified_gates"], 131)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_131_gates_verified)
        self.assertFalse(rep.all_134_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 134)

    def test_57_stub_134gate_dry_run_134_of_134(self) -> None:
        rep = evaluate_134_master_safety_gates(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_132_override=_make_stub_master132(dry_run=True),
        )
        self.assertEqual(rep.summary["verified_gates"], 134)
        self.assertTrue(rep.all_134_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_58_g133_failure_propagates_to_134gate_report(self) -> None:
        rep = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=True),
            steadyshot_selftimer_kwargs={"requested_movie_steadyshot": "Dynamic active"},
        )
        self.assertFalse(rep.g133_to_g134_all_passed)
        self.assertFalse(rep.all_134_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G133_STEADYSHOT_ACTIVE_LOCKOUT_OR_DYNAMIC_VIOLATION
        )

    def test_59_g134_failure_propagates_to_134gate_report(self) -> None:
        rep = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=True),
            zebra_peaking_streaming_kwargs={
                "requested_airplane_mode": "On",
                "requested_net_interface": NET_IFACE_WIFI_G134,
                "requested_network_op": NET_OP_STREAM_ONLY_G134,
            },
        )
        self.assertFalse(rep.g133_to_g134_all_passed)
        self.assertFalse(rep.all_134_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION
        )

    def test_60_g132_failure_propagates_to_134gate_report(self) -> None:
        stub132 = _make_stub_master132(dry_run=True, all_g13_132_ok=False)
        bad132 = dataclasses.replace(
            stub132,
            status=STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )
        rep = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=bad132,
        )
        self.assertFalse(rep.g13_to_g134_all_passed)
        self.assertFalse(rep.all_134_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )

    def test_61_persistent_emmc_write_blocks_134gate_report(self) -> None:
        rep = run_134_gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_132_override=_make_stub_master132(dry_run=True),
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_134_gates_verified)

    def test_62_real_chained_134gate_offline_and_dry_run(self) -> None:
        off = evaluate_134gate_preflight(DEFAULT_REPO_ROOT)
        self.assertGreaterEqual(off.summary["verified_gates"], 131)
        self.assertEqual(off.summary["verified_gates"], 131)
        self.assertTrue(off.offline_131_gates_verified)
        self.assertFalse(off.overall_ready_for_hardware_attach)
        self.assertEqual(off.raw_firmware_bytes_leaked, 0)

        dry = evaluate_134gate_preflight(
            DEFAULT_REPO_ROOT, simulate_bench_dry_run=True
        )
        self.assertGreaterEqual(dry.summary["verified_gates"], 134)
        self.assertEqual(dry.summary["verified_gates"], 134)
        self.assertTrue(dry.all_134_gates_verified)
        self.assertFalse(dry.overall_ready_for_hardware_attach)
        self.assertFalse(dry.persistent_emmc_writes_authorized)
        self.assertFalse(dry.cross_model_flash_authorized)

    def test_63_real_chained_134gate_clean_room_forced_offline_and_dry_run(self) -> None:
        off = evaluate_134gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(off.summary["verified_gates"], 131)
        self.assertTrue(off.offline_131_gates_verified)

        dry = evaluate_134gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(dry.summary["verified_gates"], 134)
        self.assertTrue(dry.all_134_gates_verified)

    def test_64_cli_help_python314_percent_escaping(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("verify-steadyshot-selftimer-guard", out)
        self.assertIn("verify-zebra-peaking-streaming-firewall-guard", out)
        self.assertIn("verify-134-gates", out)

    def test_65_cli_g133_g134_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-steadyshot-selftimer-guard",
            "verify-zebra-peaking-streaming-firewall-guard",
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf_j.getvalue())
            self.assertTrue(data["valid"])
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

            buf_t = io.StringIO()
            with contextlib.redirect_stdout(buf_t):
                rc2 = cli_main([cmd, "--clean-room"])
            self.assertEqual(rc2, 0)
            self.assertIn("valid=True", buf_t.getvalue())

    def test_66_cli_verify_134_gates_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-134-gates",
                "--simulate-bench-dry-run",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["status"], "VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 134)
        self.assertEqual(payload["g133_status"], STATUS_VERIFIED_G133)
        self.assertEqual(payload["g134_status"], STATUS_VERIFIED_G134)

    def test_67_cli_verify_134_gates_clean_room_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-134-gates",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            payload["status"], "VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 131)

    def test_68_cli_verify_134_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-134-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0", out)
        self.assertIn("verified=131/134", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_69_cli_aliases_work_cleanly(self) -> None:
        for alias in (
            "verify-g133-steadyshot-selftimer",
            "verify-g134-zebra-streaming-firewall",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([alias, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])

    def test_70_module_direct_main_entrypoint(self) -> None:
        for gate_flag in ("g133", "g134", "134"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(
                    ["--gate", gate_flag, "--clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["status"] if gate_flag != "134" else data["g133_status"],
                STATUS_VERIFIED_G133
                if gate_flag in ("g133", "134")
                else STATUS_VERIFIED_G134,
            )

    def test_71_g133_combined_4_lockout_reasons_reported_together(self) -> None:
        res = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE305,
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            movie_rec_frame_rate="119.88p",
            sq_frame_rate="120fps",
            hdmi_raw_output_on=True,
            de_squeeze_ratio=DESQUEEZE_1_5X_G133,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.movie_active_locked_out)
        self.assertEqual(len(res.movie_active_lockout_reasons), 4)
        self.assertEqual(res.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)

    def test_72_g133_clear_image_zoom_allowed_in_still_jpeg_only(self) -> None:
        ok = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE305,
            still_raw_capture=False,
            clear_image_zoom_on=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.clear_image_zoom_available)

    def test_73_g133_hdmi_audio_does_not_suppress_still_mode_audio_signals(self) -> None:
        ok = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE305,
            silent_mode_on=False,
            hdmi_audio_during_movie_rec=True,
            requested_audio_signals=AUDIO_SIGNALS_ON_G133,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.audio_signals_suppressed)
        self.assertEqual(ok.effective_audio_signals, AUDIO_SIGNALS_ON_G133)

    def test_74_g133_front_lamp_inactive_when_single_shooting_drive(self) -> None:
        ok = verify_steadyshot_and_selftimer_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE305,
            requested_drive_mode=DRIVE_MODE_SINGLE_SHOOTING_G133,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.front_selftimer_lamp_active)

    def test_75_g134_streaming_rec_dur_disabled_has_no_forced_rec_fps(self) -> None:
        ok = verify_zebra_peaking_streaming_firewall_guard(
            streaming_active=True,
            streaming_resolution=STREAM_RES_4K_G134,
            streaming_frame_rate="29.97p",
            requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_DISABLE_G134,
            requested_internal_rec_resolution=STREAM_RES_4K_G134,
        )
        self.assertTrue(ok.valid)
        self.assertIsNone(ok.forced_internal_rec_frame_rate)
        self.assertTrue(ok.internal_4k_rec_blocked_by_stream)

    def test_76_g134_streaming_hd_allows_internal_4k_rec_when_enabled_on_slot2(self) -> None:
        for res_mode in (STREAM_RES_HD_1080_G134, STREAM_RES_HD_720_G134):
            ok = verify_zebra_peaking_streaming_firewall_guard(
                streaming_active=True,
                streaming_resolution=res_mode,
                streaming_frame_rate="59.94p",
                requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
                requested_internal_rec_resolution=STREAM_RES_4K_G134,
                requested_target_slot=MEDIA_SLOT_2_PHASE305,
                requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            )
            self.assertTrue(ok.valid)
            self.assertFalse(ok.internal_4k_rec_blocked_by_stream)
            self.assertEqual(ok.forced_internal_rec_frame_rate, "59.94p")

    def test_77_g134_multiple_simultaneous_violations_collect_all_codes(self) -> None:
        bad = verify_zebra_peaking_streaming_firewall_guard(
            custom1_standard_ire=120,
            fx6_zebra_setting="Both",
            streaming_frame_rate="23.98p",
            requested_net_interface=NET_IFACE_WIFI_G134,
            requested_network_op=NET_OP_STREAM_WITH_INTERNAL_REC_G134,
            requested_movie_rec_during_streaming=MOVIE_REC_DURING_STREAMING_ENABLE_G134,
            requested_target_slot=MEDIA_SLOT_1_PHASE305,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G134_ZEBRA_CUSTOM12_PEAKING_OR_RESET_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G134_FX6_ZEBRA_BOTH_OR_CLEAN_HDMI_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G134_STREAMING_PROTOCOL_FPS_OR_4K_REC_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G134_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
            bad.violation_codes,
        )

    def test_78_g133_multiple_simultaneous_violations_collect_all_codes(self) -> None:
        bad = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot="Dynamic active",
            requested_focal_length_mm=99,
            movie_self_timer_requested=True,
            claimed_fx3_supports_audio_signal_volume=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(len(bad.violation_codes), 4)

    def test_79_cli_full_json_payload_contains_134_gates_and_redlines(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-134-gates", "--clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(len(data["gates"]), 134)
        self.assertEqual(data["gates"][-2]["gate_id"], G133_GATE_ID)
        self.assertEqual(data["gates"][-2]["gate_code"], G133_GATE_CODE)
        self.assertEqual(data["gates"][-1]["gate_id"], G134_GATE_ID)
        self.assertEqual(data["gates"][-1]["gate_code"], G134_GATE_CODE)
        self.assertFalse(data["hardware_live_attachment_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_80_h0_h1_trial_entry_blocked_if_persistent_emmc_or_g133_fails(self) -> None:
        rep_bad_g133 = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=False),
            steadyshot_selftimer_kwargs={"movie_self_timer_requested": True},
        )
        self.assertFalse(rep_bad_g133.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep_bad_g133.status,
            STATUS_BLOCKED_G133_DORMANT_MOVIE_OR_PORTRAIT_SELFTIMER_VIOLATION,
        )

        rep_emmc = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=False),
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.h0_h1_trial_entry_allowed)

    def test_81_module_main_text_output_g133_g134_134(self) -> None:
        for flag in ("g133", "g134", "134"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", flag, "--clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("STATUS_VERIFIED" if flag != "134" else "131/134", buf.getvalue())

    def test_82_fx3_clean_room_test_env_propagates_to_134_gates_subprocess(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env[ENV_CLEAN_ROOM_TEST_PHASE305] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-g133-steadyshot-selftimer",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["focal_length_table_count"], 47)

    def test_83_fx3_identity_constants_phase305_match_fx3_v702(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE305, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE305, 0x39383232)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE305, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE305, "7.02")

    def test_84_g134_zebra_display_ignores_non_log_display_lut_flag(self) -> None:
        res = verify_zebra_peaking_streaming_firewall_guard(
            log_shooting_on=False,
            display_lut_on=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.zebra_measures_post_lut_display)

    def test_85_g133_movie_rec_fps_numeric_boundary_999_vs_100(self) -> None:
        res_5994 = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            movie_rec_frame_rate="59.94p",
            sq_frame_rate="60fps",
        )
        self.assertTrue(res_5994.valid)
        self.assertFalse(res_5994.movie_active_locked_out)
        self.assertEqual(res_5994.effective_movie_steadyshot, MOVIE_STEADYSHOT_ACTIVE_G133)

        res_100 = verify_steadyshot_and_selftimer_guard(
            requested_movie_steadyshot=MOVIE_STEADYSHOT_ACTIVE_G133,
            movie_rec_frame_rate="100p",
        )
        self.assertTrue(res_100.valid)
        self.assertTrue(res_100.movie_active_locked_out)
        self.assertEqual(res_100.effective_movie_steadyshot, MOVIE_STEADYSHOT_STANDARD_G133)

    def test_86_g134_offline_report_to_dict_json_roundtrip(self) -> None:
        rep = evaluate_134gate_preflight(
            force_clean_room=True,
            master_132_override=_make_stub_master132(dry_run=False),
        )
        blob = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(blob)
        self.assertEqual(decoded["summary"]["total_gates"], 134)
        self.assertEqual(decoded["summary"]["verified_gates"], 131)
        self.assertEqual(decoded["g133_result"]["status"], STATUS_VERIFIED_G133)
        self.assertEqual(decoded["g134_result"]["status"], STATUS_VERIFIED_G134)


if __name__ == "__main__":
    unittest.main()
